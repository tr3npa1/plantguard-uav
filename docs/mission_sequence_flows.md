# PlantGuard UAV — Mission Sequence Flows

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Mission Sequence Flows |
| Target release | v1.0 |
| Status | Active architecture baseline |
| Related documents | `docs/system_architecture.md`, `docs/component_catalog.md`, `docs/component_interfaces.md`, `docs/runtime_and_deployment_architecture.md`, `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md`, `docs/verification_and_acceptance_plan.md`, `docs/v1_scope_baseline.md` |
| Last updated | 2026-07-21 |

## 1. Document Purpose

This document defines the cross-component sequence flows for PlantGuard UAV v1.0.

It describes:

- the active mission state;
- participating components;
- commands;
- events;
- synchronous acknowledgments;
- asynchronous jobs;
- persistence actions;
- artifact writes;
- failure propagation;
- safe next states;
- processing-resume behavior;
- physical-flight recovery behavior.

This document is the authoritative workflow-level explanation of how the system behaves over time.

It does not define exact source-code syntax, API paths, queue implementations, database tables, or PX4 configuration values.

## 2. Sequence-Flow Conventions

## 2.1 Interaction Symbols

```text
A → B: Command
A ← B: Immediate acknowledgment or query result
A ⇒ B: Event
A ⇢ B: Asynchronous job submission
A ⇠ B: Job progress or completion event
```

## 2.2 Persistence Notation

```text
[DB]       Structured authoritative record
[ARTIFACT] File-oriented mission evidence
[EVENT]    Append-only operational/audit event
```

## 2.3 Ownership Rules

Every flow obeys the following:

```text
Mission Orchestrator
→ owns workflow progression and mission-state transitions

Safety Supervisor
→ owns application-level safety decisions

PX4/MAVSDK Vehicle Adapter
→ owns application-to-vehicle command translation

PX4
→ owns low-level flight execution and native failsafes

Workers and model services
→ process evidence but never command the aircraft

Persistence Layer
→ stores authoritative structured records

Mission Data Manager
→ owns artifact relationships and traceability
```

## 2.4 Command Acceptance Versus Completion

A command acknowledgment confirms that the receiver accepted or rejected the request.

It does not prove that the physical or computational action completed.

Example:

```text
ReturnHome accepted
≠
HomeReached
≠
VehicleLanded
```

## 2.5 Partial-Evidence Rule

Whenever a flow fails:

- already captured images are preserved;
- completed processing outputs are preserved;
- incomplete work is marked honestly;
- unresolved sites remain visible;
- no prediction is invented;
- physical flight is not automatically resumed.

## 3. Canonical State Dimensions and Flow Notation

Authoritative workflow state:

```text
created
preparing
awaiting_operator_approval
ready
active
post_flight_processing
report_ready
complete
aborted
failed
```

Mission activity:

```text
configuration
technical_preflight
takeoff
survey
same_flight_decision
revisit
return_home
landing
none
```

Vehicle operational state and processing-job state are separate dimensions defined by the data and interface contracts. Only the Mission Orchestrator changes workflow state; PX4/Vehicle Adapter reports vehicle state; the worker owns job state.

For compactness, later flow blocks may use activity aliases such as `preflight`, `takeoff`, `survey`, `initial_analysis`, `revisit_planning`, `revisit`, `final_classification`, `return_to_home`, `landing`, and `report_generation`. These aliases are not additional workflow-state enum values. Processing aliases may overlap vehicle return or landing.

## 4. Canonical Final Site Statuses

```text
healthy
healthy_after_suspicious_survey
unhealthy_disease_identified
unhealthy_disease_uncertain
health_status_unresolved
manual_inspection_recommended
revisit_not_completed
```

`revisit_capture_failed` is a reason code attached to `revisit_not_completed`, not an additional final status. Manual-inspection and uncertainty outcomes remain visible but do not count as automatic site resolution.

## 5. Normal End-to-End Mission Overview

```text
Farmer selects field
→ mission is created
→ farmer confirms automatic coverage and exclusions
→ Survey Planner generates candidate route
→ Safety Supervisor validates route and technical preflight
→ farmer approves takeoff
→ Safety Supervisor validates final takeoff authorization
→ PX4 takes off and executes survey
→ camera captures images
→ images are validated
→ aerial screening produces observations
→ suspicious observations are clustered
→ Revisit Planner creates candidate revisit route
→ Safety Supervisor approves safe revisit subset
→ PX4 executes revisit
→ revisit images are validated
→ health is reassessed
→ disease classification runs where appropriate
→ multi-image evidence is aggregated
→ PX4 returns and lands
→ maps and reports are generated
→ mission completes
```

# Part I — Mission Setup and Survey

## 6. Flow 1 — Field Selection

### Initial State

```text
idle
```

### Participants

- Farmer;
- Farmer Dashboard;
- Mission API;
- Persistence Layer;
- Observability and Event Logger.

### Sequence

1. Farmer selects a saved field in the Dashboard.
2. Dashboard → Mission API: `SelectField`.
3. Mission API validates:
   - field identifier;
   - operator authorization;
   - field availability;
   - field-definition version.
4. Mission API queries the Persistence Layer.
5. Persistence Layer returns:
   - field boundary;
   - saved home location;
   - exclusion zones;
   - saved metadata;
   - field version.
6. Mission API returns the field summary to the Dashboard.
7. Dashboard displays:
   - field boundary;
   - current exclusions;
   - route-intent controls;
   - compatibility warnings.
8. Observability records the field-selection action.

### Persistence

```text
[EVENT] FieldSelectedByOperator
```

Selection may be treated as UI/session state until mission creation.

### Failure Behavior

- Unknown field: reject with `not_found`.
- Unauthorized operator: reject with `authorization_error`.
- Invalid field geometry: display configuration error; mission creation remains blocked.
- Persistence unavailable: reject; do not cache field as authoritative.

### Next State

```text
idle
```

The system remains idle until mission creation.

## 7. Flow 2 — Mission Creation

### Initial State

```text
idle
```

### Participants

- Farmer Dashboard;
- Mission API;
- Mission Orchestrator;
- Model Registry and Metadata Manager;
- Mission Data Manager;
- Persistence Layer;
- Observability and Event Logger.

### Sequence

1. Dashboard → Mission API: `CreateMission`.
2. Request includes:
   - field ID;
   - operator ID;
   - mission profile;
   - requested route mode;
   - requested model/configuration profile;
   - idempotency key.
3. Mission API validates transport and authorization.
4. Mission API → Mission Orchestrator: `CreateMission`.
5. Mission Orchestrator requests:
   - field definition;
   - active configuration;
   - active model contracts.
6. Model Registry validates required model metadata.
7. Mission Data Manager prepares the mission artifact namespace.
8. Persistence Layer transaction creates:
   - mission record;
   - initial mission-state record;
   - configuration snapshot reference;
   - model snapshot references.
9. Artifact storage receives initial:
   - mission configuration;
   - software-version snapshot;
   - model-metadata snapshot.
10. Mission Orchestrator ⇒ subscribers: `MissionCreated`.
11. Mission Orchestrator changes state:

```text
idle → preflight
```

12. Mission Orchestrator ⇒ subscribers: `MissionStateChanged`.
13. Dashboard displays the new mission ID and setup status.

### Persistence

```text
[DB] Mission
[DB] MissionState
[DB] ConfigurationSnapshotReference
[DB] ModelSnapshotReferences
[ARTIFACT] mission_config.yaml
[ARTIFACT] software_version.json
[ARTIFACT] model_metadata.json
[EVENT] MissionCreated
[EVENT] MissionStateChanged
```

### Idempotency

A repeated `CreateMission` with the same idempotency key returns the existing mission.

A conflicting payload using the same key is rejected.

### Failure Behavior

- Model contract invalid: mission remains blocked before flight.
- Artifact namespace cannot be created: mission creation fails.
- Database transaction fails: no mission is advertised as created.
- Artifact write succeeds but database commit fails: preserve artifact as unreferenced temporary data and schedule reconciliation.

### Next State

```text
preflight
```

## 8. Flow 3 — Route-Intent Submission

### Initial State

```text
preflight
```

### Participants

- Farmer;
- Farmer Dashboard;
- Mission API;
- Mission Orchestrator;
- Survey Planner;
- Geospatial Mapper/shared geospatial utilities;
- Persistence Layer;
- Mission Data Manager;
- Observability and Event Logger.

### Supported Mode

```text
automatic_coverage
```

### Sequence

1. Farmer confirms automatic coverage for the selected field sector.
2. Farmer may define approved exclusion zones.
3. Dashboard validates basic geometry for immediate user feedback.
4. Dashboard → Mission API: `SubmitRouteIntent`.
5. Mission API validates payload shape and permissions.
6. Mission API → Mission Orchestrator: accepted route-intent command.
7. Mission Orchestrator persists route intent.
8. Mission Orchestrator → Survey Planner: `GenerateSurveyPlan`.
9. Survey Planner:
   - loads field boundary;
   - applies exclusion zones;
   - loads sweep direction, altitude, speed, and overlap from versioned mission configuration;
   - generates candidate waypoints;
   - generates capture points;
   - estimates distance and duration;
   - calculates coverage;
   - calculates skipped-area geometry.
10. Survey Planner ⇒ Mission Orchestrator: `SurveyPlanGenerated`.
11. Mission Data Manager stores route preview and planning metadata.
12. Dashboard queries and displays:
   - candidate route;
   - expected coverage;
   - skipped region;
   - warnings;
   - estimated duration.

### Coverage Warning

When exclusions reduce coverage, Dashboard displays:

```text
The excluded area will not be inspected.
Final field-health percentages will describe only the surveyed region.
```

### Persistence

```text
[DB] RouteIntent
[DB] CandidateSurveyRoute
[DB] RoutePlanningWarnings
[ARTIFACT] route_preview.geojson
[ARTIFACT] skipped_areas.geojson
[EVENT] RouteIntentSubmitted
[EVENT] SurveyPlanGenerated
```

### Failure Behavior

- Unsupported priority, guided, or custom-route input: reject with a v1.0 scope error.
- Route cannot cover valid field region: reject or return explicit incomplete-coverage warning.
- Route leaves field/exclusion rules: candidate is rejected before safety approval.
- Planner failure: mission remains in `preflight`; no executable route exists.

### Next State

```text
preflight
```

## 9. Flow 4 — Survey-Plan Safety Validation

### Initial State

```text
preflight
```

### Participants

- Mission Orchestrator;
- Safety Supervisor;
- Survey Planner;
- Persistence Layer;
- Observability and Event Logger.

### Sequence

1. Mission Orchestrator → Safety Supervisor: `ValidateSurveyPlan`.
2. Payload includes:
   - candidate route ID;
   - field and exclusion geometry;
   - home location;
   - operating limits;
   - route estimates;
   - current configuration.
3. Safety Supervisor validates:
   - geofence containment;
   - altitude constraints;
   - route continuity;
   - prohibited areas;
   - configured speed;
   - expected mission duration;
   - provisional energy feasibility;
   - route semantics.
4. Safety Supervisor returns one of:

```text
approved
approved_with_restrictions
rejected
```

5. Restrictions may:
   - reduce speed;
   - remove segments;
   - increase reserve;
   - reduce coverage;
   - require operator warning.
6. Safety decision is persisted.
7. Dashboard displays route approval status.

### Persistence

```text
[DB] SurveyRouteSafetyDecision
[EVENT] SurveyPlanApproved
or
[EVENT] SurveyPlanRestricted
or
[EVENT] SurveyPlanRejected
```

### Failure Behavior

- Safety Supervisor unavailable: route cannot be approved.
- Route rejected: mission remains `preflight`.
- Restricted route: planner may regenerate or operator accepts visible restrictions.
- No route reaches the Vehicle Adapter during this flow.

### Next State

```text
preflight
```

## 10. Flow 5 — Technical Preflight

### Initial State

```text
preflight
```

### Participants

- Mission Orchestrator;
- Safety Supervisor;
- Vehicle Adapter;
- Camera Manager;
- Model Registry;
- Persistence Layer;
- Mission Data Manager;
- Observability and Event Logger.

### Sequence

1. Mission Orchestrator gathers current readiness:
   - PX4 connection;
   - telemetry freshness;
   - GPS health;
   - home position;
   - battery;
   - approved route;
   - camera readiness;
   - test capture;
   - storage capacity/writability;
   - required model readiness;
   - worker readiness;
   - dry-daylight environment checks;
   - operator-supervision readiness.
2. Mission Orchestrator → Safety Supervisor: `RunPreflight`.
3. Safety Supervisor evaluates each check.
4. Safety Supervisor returns:

```text
PASS
WARNING
BLOCKED
```

5. Technical-preflight result includes:
   - check-level status;
   - warnings;
   - blockers;
   - validity/expiry conditions;
   - source snapshot references.
6. Result is persisted.
7. Mission Orchestrator:
   - keeps workflow `preparing` with activity `technical_preflight` for `BLOCKED`;
   - may remain `preparing` until warnings are acknowledged;
   - transitions workflow to `awaiting_operator_approval` for valid PASS/WARNING policy.
8. Mission Orchestrator ⇒ subscribers: `MissionStateChanged`.
9. Dashboard displays every check and operator action required.

### Persistence

```text
[DB] PreflightResult
[DB] PreflightCheckResults
[ARTIFACT] preflight_snapshot.json
[EVENT] PreflightCompleted
[EVENT] MissionStateChanged
```

### Failure Behavior

- PX4 disconnected: BLOCKED.
- GPS not acceptable: BLOCKED.
- Required model unavailable: BLOCKED.
- Camera unavailable: BLOCKED.
- Storage unwritable: BLOCKED.
- Weather outside policy: BLOCKED.
- Warning accepted only when policy permits.

### Next State

```text
awaiting_operator_approval
```

or remains:

```text
preflight
```

## 11. Flow 6 — Operator Approval and Final Takeoff Authorization

### Initial State

```text
awaiting_operator_approval
```

### Participants

- Farmer/operator;
- Dashboard;
- Mission API;
- Mission Orchestrator;
- Safety Supervisor;
- Persistence Layer;
- Observability and Event Logger.

### Sequence

1. Dashboard presents:
   - route;
   - expected coverage;
   - exclusions;
   - warnings;
   - battery;
   - production-environment status;
   - readiness checks.
2. Operator confirms the takeoff area and VLOS conditions.
3. Dashboard → Mission API: `ApproveTakeoff`.
4. Mission API validates actor authorization.
5. Mission API → Mission Orchestrator: approval command.
6. Mission Orchestrator verifies:
   - state still `awaiting_operator_approval`;
   - preflight is not expired;
   - route approval is current;
   - no new blocker exists.
7. Approval is persisted with the preflight, route, configuration, actor, and expiry references.
8. Mission Orchestrator → Safety Supervisor: `ValidateTakeoffAuthorization` using the latest telemetry.
9. Safety Supervisor returns `AUTHORIZED` or `REJECTED` with reasons.
10. On authorization, Mission Orchestrator transitions workflow:

```text
awaiting_operator_approval → ready
```

11. Mission Orchestrator ⇒ subscribers:
   - `TakeoffApprovalRecorded`;
   - `TakeoffAuthorizationValidated`;
   - `MissionStateChanged`.

### Persistence

```text
[DB] OperatorApproval
[DB] FinalTakeoffSafetyDecision
[EVENT] TakeoffApprovalRecorded
[EVENT] TakeoffAuthorizationValidated
[EVENT] MissionStateChanged
```

### Idempotency

Duplicate approval does not create duplicate takeoff commands.

### Failure Behavior

- Preflight expired: return workflow to `preparing` and rerun technical preflight.
- New safety blocker: reject, invalidate readiness, and return workflow to `preparing`.
- Unauthorized actor: reject.
- Persistence failure: approval is not acted upon.

### Next State

```text
ready
```

## 12. Flow 7 — Takeoff

### Initial State

```text
workflow: ready
activity: none
vehicle: on_ground
```

### Participants

- Mission Orchestrator;
- Safety Supervisor;
- Vehicle Adapter;
- PX4;
- Persistence Layer;
- Observability and Event Logger;
- Dashboard.

### Sequence

1. Mission Orchestrator verifies the current `TakeoffAuthorizationValidated` record and transitions workflow to `active` with activity `takeoff`.
2. Mission Orchestrator → Vehicle Adapter: `Takeoff`.
3. Command contains:
   - mission ID;
   - operator-approval reference;
   - safety-decision reference;
   - target takeoff altitude;
   - idempotency key.
4. Vehicle Adapter validates command envelope and current PX4 state.
5. Vehicle Adapter → PX4: takeoff request.
6. Vehicle Adapter acknowledges command handling.
7. PX4 arms and begins takeoff.
8. Vehicle Adapter ⇒ subscribers: `TakeoffStarted`.
9. Telemetry updates continue.
10. PX4 reaches the target takeoff condition.
11. Vehicle Adapter ⇒ subscribers: `TakeoffCompleted`.
12. Mission Orchestrator persists completion.
13. Mission Orchestrator changes activity:

```text
takeoff → survey
```

14. Mission Orchestrator ⇒ subscribers: `MissionStateChanged` with workflow still `active`.

### Persistence

```text
[DB] VehicleCommand
[DB] TakeoffResult
[EVENT] TakeoffStarted
[EVENT] TakeoffCompleted
[EVENT] MissionStateChanged
```

### Failure Behavior

- Command rejected before arming: return to `ready` if authorization remains valid, otherwise `preparing`; transition to `failed` only when the mission cannot recover safely.
- Partial takeoff failure: Safety Supervisor determines hold, land, or return.
- Duplicate command: Vehicle Adapter returns existing command result.
- Manual takeover: follow manual-takeover flow.

### Next State

```text
survey
```

# Part II — Survey Capture and Initial Analysis

## 13. Flow 8 — Route Upload and Survey Start

### Initial State

```text
survey
```

### Participants

- Mission Orchestrator;
- Vehicle Adapter;
- PX4;
- Camera Manager;
- Safety Supervisor;
- Observability.

### Sequence

1. Mission Orchestrator → Vehicle Adapter: `UploadRoute`.
2. Command includes approved route and safety decision.
3. Vehicle Adapter → PX4: upload mission.
4. Vehicle Adapter ⇒ Mission Orchestrator: `RouteUploaded`.
5. Mission Orchestrator performs current safety revalidation.
6. Mission Orchestrator → Vehicle Adapter: `StartSurvey`.
7. Vehicle Adapter → PX4: start uploaded mission.
8. Vehicle Adapter ⇒ subscribers: `SurveyStarted`.
9. Vehicle Adapter publishes:
   - progress;
   - active waypoint;
   - telemetry;
   - route deviations.
10. Camera Manager receives capture triggers or route/capture context.

### Persistence

```text
[DB] UploadedRouteReference
[DB] SurveyExecutionRecord
[EVENT] RouteUploaded
[EVENT] SurveyStarted
[EVENT] SurveyProgressUpdated
```

### Failure Behavior

- Upload fails: no survey execution; safe hold/land/return policy.
- Route approval stale: block start and revalidate.
- PX4 rejects route: record exact reason.
- Telemetry stale: no new start command.

### Next State

```text
survey
```

## 14. Flow 9 — Survey Image Capture

### Initial State

```text
survey
```

### Participants

- PX4;
- Vehicle Adapter;
- Mission Orchestrator;
- Camera Manager;
- Mission Data Manager;
- Artifact Storage;
- Persistence Layer;
- Observability.

### Sequence

For every planned capture opportunity:

1. Vehicle Adapter publishes current waypoint and telemetry.
2. Capture coordinator → Camera Manager: `CaptureImage`.
3. Camera Manager associates:
   - logical capture ID;
   - mission ID;
   - route ID;
   - waypoint/capture-point ID;
   - timestamp;
   - telemetry snapshot.
4. Camera Manager triggers physical capture.
5. Camera returns image bytes/file.
6. Mission Data Manager allocates mission-scoped artifact path.
7. Image is written to a temporary path.
8. Image completeness/readability is minimally verified.
9. Artifact is atomically promoted to final raw-image path.
10. Structured image record is persisted.
11. Camera Manager ⇒ subscribers: `ImageCaptured`.
12. Observability records capture latency and failures.

### Persistence

```text
[DB] ImageRecord
[DB] CaptureEvent
[ARTIFACT] raw survey image
[EVENT] ImageCaptured
```

### Retry Behavior

- Same logical capture request is duplicate-safe.
- A new physical retry image uses a new image ID linked to the same capture opportunity.
- Retry limit is configuration-controlled.

### Failure Behavior

- Single capture fails: retry where safe; preserve failure record.
- Repeated/global camera failure: invoke camera-failure flow.
- Artifact write fails: do not emit `ImageCaptured` as complete.
- Database write fails after artifact write: preserve artifact and schedule reconciliation.

### Next State

```text
survey
```

## 15. Flow 10 — Survey Completion

### Initial State

```text
survey
```

### Participants

- PX4;
- Vehicle Adapter;
- Mission Orchestrator;
- Camera Manager;
- Safety Supervisor;
- Persistence Layer;
- Observability.

### Sequence

1. PX4 completes the approved survey route.
2. Vehicle Adapter ⇒ subscribers: `SurveyCompleted`.
3. Camera Manager flushes pending capture records.
4. Mission Data Manager verifies manifest consistency.
5. Mission Orchestrator checks:
   - survey execution outcome;
   - capture success count;
   - storage state;
   - vehicle state;
   - battery;
   - link health.
6. Mission Orchestrator transitions:

```text
survey → initial_analysis
```

7. Mission Orchestrator ⇒ subscribers: `MissionStateChanged`.
8. Depending on architecture/mission mode:
   - drone may hold at a safe location;
   - drone may loiter under approved policy;
   - drone may return before post-flight processing;
   - analysis may begin while vehicle remains airborne only when safety permits.

### Persistence

```text
[DB] SurveyCompletion
[ARTIFACT] capture_events.csv
[ARTIFACT] mission_manifest.csv
[EVENT] SurveyCompleted
[EVENT] MissionStateChanged
```

### Failure Behavior

- Incomplete route: preserve covered region and reason.
- Battery no longer supports same-flight analysis/revisit: return-home path.
- Manifest inconsistency: block perception until reconciled.
- Post-flight mode: proceed to return-home before analysis.

### Next State

```text
initial_analysis
```

or:

```text
return_to_home
```

for post-flight/degraded operation.

## 16. Flow 11 — Image-Quality Validation

### Initial State

```text
initial_analysis
```

### Participants

- Mission Orchestrator;
- Background Job Worker;
- Image Quality Validator;
- Mission Data Manager;
- Persistence Layer;
- Artifact Storage;
- Observability.

### Sequence

1. Mission Orchestrator gathers raw survey-image references.
2. Mission Orchestrator ⇢ Worker: `ValidateMissionImages`.
3. Worker creates a checkpointable job.
4. For each image:
   1. Worker invokes Image Quality Validator.
   2. Validator checks readability, blur, exposure, obstruction, visibility, size, and metadata.
   3. Validator returns accepted or rejected result.
   4. Result is persisted.
   5. Accepted/rejected manifests are updated.
   6. Worker emits progress.
5. Worker ⇠ Mission Orchestrator:
   - `ImageValidationCompleted`;
   - accepted count;
   - rejected count;
   - failures;
   - checkpoint.
6. Mission Data Manager validates manifest links.

### Persistence

```text
[DB] ImageQualityResult
[ARTIFACT] accepted_images.csv
[ARTIFACT] rejected_images.csv
[EVENT] ImageAccepted
[EVENT] ImageRejected
[EVENT] JobProgressUpdated
[EVENT] ImageValidationCompleted
```

### Failure Behavior

- Individual image validation fails: preserve image; mark retryable/incomplete.
- Worker crash: resume from checkpoint.
- Too many unusable images: follow image-quality failure flow.
- No accepted images: automatic screening cannot proceed.

### Next State

```text
initial_analysis
```

## 17. Flow 12 — Aerial Health Screening

### Initial State

```text
initial_analysis
```

### Participants

- Mission Orchestrator;
- Background Worker;
- Aerial Health Screening Service;
- Model Registry;
- Mission Data Manager;
- Persistence Layer;
- Artifact Storage;
- Observability.

### Sequence

1. Mission Orchestrator obtains accepted survey-image references.
2. Model Registry supplies a versioned screening contract.
3. Mission Orchestrator ⇢ Worker: `ScreenSurveyImages`.
4. For each accepted image or tile:
   1. load artifact by reference;
   2. apply versioned preprocessing;
   3. run inference;
   4. validate output shape and semantics;
   5. create healthy, unhealthy, or uncertain observations;
   6. persist observation records;
   7. store prediction artifacts where required;
   8. emit progress and per-image completion.
5. Worker produces:
   - observation references;
   - counts by health status;
   - failed-image list;
   - timing metrics;
   - checkpoint.
6. Worker ⇒ subscribers: `SurveyScreeningCompleted`.

### Persistence

```text
[DB] SurveyObservation
[DB] ScreeningJobResult
[ARTIFACT] screening_predictions.csv
[ARTIFACT] optional prediction overlays
[EVENT] SurveyImageScreened
[EVENT] SurveyScreeningCompleted
```

### Failure Behavior

- Invalid model output: reject that output; never force status.
- Model runtime crash: preserve checkpoint and source evidence.
- Screening job cannot complete: automatic same-flight revisit generation is disabled.
- Completed observations remain valid and preserved.

### Next State

```text
initial_analysis
```

## 18. Flow 13 — Suspicious-Site Clustering

### Initial State

```text
initial_analysis
```

### Participants

- Mission Orchestrator;
- Background Worker;
- Suspicious-Site Clusterer;
- Geospatial Mapper/shared utilities;
- Persistence Layer;
- Mission Data Manager;
- Observability.

### Sequence

1. Mission Orchestrator gathers:
   - unhealthy observations;
   - uncertain observations;
   - geographic metadata;
   - clustering configuration.
2. Mission Orchestrator ⇢ Worker: `ClusterSuspiciousObservations`.
3. Clusterer:
   - rejects observations lacking required spatial context according to policy;
   - groups geographically related observations;
   - suppresses duplicates;
   - selects representative site locations;
   - records supporting observations;
   - calculates priority evidence.
4. For each new group:
   - persist suspicious-site record;
   - persist membership;
   - emit `SuspiciousSiteCreated`.
5. For merged evidence:
   - update site;
   - emit `SuspiciousSiteUpdated`.
6. Worker emits `SuspiciousSiteClusteringCompleted`.

### Persistence

```text
[DB] SuspiciousSite
[DB] SiteObservationMembership
[ARTIFACT] suspicious_sites.csv
[EVENT] SuspiciousSiteCreated
[EVENT] SuspiciousSiteUpdated
[EVENT] SuspiciousSiteClusteringCompleted
```

### Failure Behavior

- Source observations remain preserved.
- No untraceable site is created.
- Revisit planning is unavailable until clustering succeeds.
- Retry from the original observation set.

### Next State

If suspicious sites exist and same-flight revisit is feasible:

```text
revisit_planning
```

If no suspicious sites exist:

```text
return_to_home
```

If processing must finish after landing:

```text
return_to_home
```

with future recovery mission if needed.

# Part III — Revisit Planning and Execution

## 19. Flow 14 — Revisit Candidate Generation

### Initial State

```text
revisit_planning
```

### Participants

- Mission Orchestrator;
- Revisit Planner;
- Persistence Layer;
- Mission Data Manager;
- Observability.

### Sequence

1. Mission Orchestrator gathers eligible suspicious sites.
2. Mission Orchestrator → Revisit Planner: `GenerateRevisitPlan`.
3. Revisit Planner:
   - applies site priority;
   - estimates route geometry;
   - generates revisit targets;
   - estimates time and distance;
   - proposes a subset if all sites cannot fit;
   - produces candidate skip reasons.
4. Revisit Planner ⇒ subscribers: `RevisitPlanGenerated`.
5. Candidate route and targets are persisted.
6. Dashboard may display planned sites and expected unresolved sites.

### Persistence

```text
[DB] CandidateRevisitRoute
[DB] RevisitTarget
[DB] CandidateSkippedSite
[ARTIFACT] revisit_targets.csv
[ARTIFACT] revisit_route_preview.geojson
[EVENT] RevisitPlanGenerated
```

### Failure Behavior

- No eligible site: proceed to return.
- Invalid geometry: sites remain unresolved.
- Planner unavailable: preserve sites and allow later recovery mission.

### Next State

```text
revisit_planning
```

## 20. Flow 15 — Revisit Safety Validation

### Initial State

```text
revisit_planning
```

### Participants

- Mission Orchestrator;
- Safety Supervisor;
- Vehicle Adapter;
- Revisit Planner;
- Persistence Layer;
- Observability.

### Sequence

1. Mission Orchestrator gets current telemetry and battery.
2. Mission Orchestrator → Safety Supervisor: `ValidateRevisitPlan`.
3. Safety Supervisor evaluates:
   - revisit route;
   - target subset;
   - current battery;
   - required return and landing energy;
   - reserve;
   - GPS;
   - link health;
   - weather;
   - altitude;
   - exclusions;
   - operator authorization policy.
4. Safety Supervisor returns:
   - approved;
   - approved with restrictions;
   - approved safe subset;
   - rejected.
5. Rejected sites receive explicit skip reason:
   - `revisit_skipped_safety`;
   - `revisit_skipped_battery`;
   - `revisit_skipped_route_invalid`;
   - `revisit_skipped_weather`.
6. Safety decision and approved subset are persisted.
7. Mission Orchestrator:
   - transitions to `revisit` when approved subset exists;
   - transitions to `return_to_home` otherwise.

### Persistence

```text
[DB] RevisitSafetyDecision
[DB] ApprovedRevisitSubset
[DB] RevisitSkipReasons
[EVENT] RevisitPlanApproved
or
[EVENT] RevisitPlanRejected
[EVENT] MissionStateChanged
```

### Safety Rule

Revisit begins only when:

```text
revisit
+ return home
+ landing
+ required reserve
```

are feasible.

### Next State

```text
revisit
```

or:

```text
return_to_home
```

## 21. Flow 16 — Revisit Route Upload and Start

### Initial State

```text
revisit
```

### Participants

- Mission Orchestrator;
- Vehicle Adapter;
- PX4;
- Safety Supervisor;
- Camera Manager;
- Observability.

### Sequence

1. Mission Orchestrator → Vehicle Adapter: `UploadRoute` with approved revisit route.
2. Vehicle Adapter → PX4: upload route.
3. Vehicle Adapter ⇒ subscribers: `RouteUploaded`.
4. Mission Orchestrator performs final current safety validation.
5. Mission Orchestrator → Vehicle Adapter: `StartRevisit`.
6. Vehicle Adapter → PX4: begin mission.
7. Vehicle Adapter ⇒ subscribers: `RevisitStarted`.
8. Telemetry and progress continue.

### Persistence

```text
[DB] RevisitExecutionRecord
[EVENT] RevisitStarted
[EVENT] RevisitProgressUpdated
```

### Failure Behavior

- Upload/start failure: return-home or hold according to safety policy.
- Route approval expired: revalidate.
- Battery drops before start: safe subset or return.

### Next State

```text
revisit
```

## 22. Flow 17 — Revisit Target Capture

### Initial State

```text
revisit
```

### Participants

- PX4;
- Vehicle Adapter;
- Mission Orchestrator;
- Camera Manager;
- Mission Data Manager;
- Artifact Storage;
- Persistence Layer;
- Observability.

### Sequence

For every approved revisit target:

1. PX4 approaches target.
2. Vehicle Adapter ⇒ subscribers: `RevisitTargetReached`.
3. Safety Supervisor validates continuing conditions from current telemetry.
4. Camera Manager receives one or more capture requests.
5. Camera Manager captures multiple views according to policy.
6. Each image is:
   - assigned an image ID;
   - linked to site and target;
   - timestamped;
   - linked to telemetry;
   - written atomically;
   - persisted.
7. Camera Manager ⇒ subscribers: `ImageCaptured`.
8. Mission Orchestrator marks target:
   - complete when capture requirement is met;
   - failed when capture cannot be completed.
9. Vehicle Adapter/Mission Orchestrator ⇒ subscribers:
   - `RevisitTargetCompleted`;
   - or `RevisitTargetFailed`.

### Persistence

```text
[DB] RevisitTargetExecution
[DB] RevisitImageRecord
[ARTIFACT] raw revisit images
[EVENT] RevisitTargetReached
[EVENT] RevisitTargetCompleted
or
[EVENT] RevisitTargetFailed
```

### Failure Behavior

- One image fails: retry within policy.
- Target capture remains unusable: set the final outcome to `revisit_not_completed` and record `revisit_capture_failed` as its reason code.
- Safety degrades: stop remaining targets and return.
- Partial target evidence is preserved.

### Next State

```text
revisit
```

until route ends.

## 23. Flow 18 — Revisit Completion

### Initial State

```text
revisit
```

### Participants

- PX4;
- Vehicle Adapter;
- Mission Orchestrator;
- Safety Supervisor;
- Mission Data Manager;
- Persistence Layer;
- Observability.

### Sequence

1. PX4 completes approved revisit subset.
2. Vehicle Adapter ⇒ subscribers: `RevisitCompleted`.
3. Mission Data Manager verifies captured revisit manifest.
4. Mission Orchestrator evaluates:
   - captured targets;
   - failed/skipped targets;
   - battery;
   - current flight state.
5. Mission Orchestrator transitions:

```text
revisit → final_classification
```

6. Depending on battery and runtime policy, analysis may:
   - begin immediately while safe;
   - begin during return;
   - begin after landing.
7. Flight safety is never delayed merely to finish inference.

### Persistence

```text
[DB] RevisitCompletion
[ARTIFACT] revisit capture manifest
[EVENT] RevisitCompleted
[EVENT] MissionStateChanged
```

### Next State

```text
final_classification
```

while flight may separately proceed to return when required.

# Part IV — Final Analysis

## 24. Flow 19 — Revisit Image-Quality Validation

### Initial State

```text
final_classification
```

### Sequence

Same validation contract as survey images, but each result is also linked to:

- site ID;
- revisit target ID;
- capture view;
- revisit stage.

Rejected revisit images remain evidence of attempted capture but do not enter normal inference.

### Persistence

```text
[DB] RevisitImageQualityResult
[ARTIFACT] accepted/rejected revisit manifests
[EVENT] ImageAccepted
[EVENT] ImageRejected
```

### Failure Behavior

When no usable revisit image exists for a site:

```text
final site path
→ revisit_not_completed
or
→ manual_inspection_recommended
```

with explicit reason.

## 25. Flow 20 — Revisit Health Reassessment

### Initial State

```text
final_classification
```

### Participants

- Mission Orchestrator;
- Background Worker;
- Revisit Health Reassessment Service;
- Model Registry;
- Persistence Layer;
- Mission Data Manager;
- Observability.

### Sequence

1. Mission Orchestrator groups accepted revisit images by site.
2. Model Registry supplies reassessment contract.
3. Mission Orchestrator ⇢ Worker: `ReassessRevisitHealth`.
4. For each accepted image:
   - preprocess;
   - infer;
   - validate output;
   - produce healthy, unhealthy, or uncertain;
   - persist confidence and metadata.
5. Worker emits per-image events and completion.

### Persistence

```text
[DB] RevisitHealthEvidence
[ARTIFACT] revisit_predictions.csv
[EVENT] RevisitImageHealthAssessed
[EVENT] RevisitHealthAssessmentCompleted
```

### Failure Behavior

- Invalid output: no forced health result.
- Unsupported crop/condition: unresolved/manual inspection.
- Runtime failure: preserve images and retry later.

### Next State

```text
final_classification
```

## 26. Flow 21 — Disease Classification

### Initial State

```text
final_classification
```

### Participants

- Revisit analysis workflow;
- Background Worker;
- PlantGuard Disease Classifier;
- Model Registry;
- Persistence Layer;
- Mission Data Manager;
- Observability.

### Preconditions

Disease classification runs only for accepted revisit imagery with sufficiently unhealthy health evidence and a supported model contract.

### Sequence

1. Analysis workflow selects eligible image evidence.
2. Model Registry validates PlantGuard classifier contract.
3. Workflow ⇢ Worker: `ClassifyDisease`.
4. For each eligible image:
   - preprocess using versioned contract;
   - run inference;
   - validate class ordering and output;
   - produce top-k predictions;
   - persist confidence;
   - emit per-image completion.
5. Unsupported or uncertain cases are recorded explicitly.

### Persistence

```text
[DB] DiseaseEvidence
[ARTIFACT] disease prediction artifacts
[EVENT] DiseaseImageClassified
[EVENT] DiseaseClassificationCompleted
```

### Failure Behavior

- Classifier unavailable: preserve health result; mark disease unresolved.
- Unsupported crop: `unsupported_crop`.
- Low confidence: `disease_confidence_too_low`.
- Similar top predictions: `top_predictions_too_similar`.
- No disease label is forced.

### Next State

```text
final_classification
```

## 27. Flow 22 — Multi-Image Evidence Aggregation

### Initial State

```text
final_classification
```

### Participants

- Mission Orchestrator;
- Background Worker;
- Multi-Image Result Aggregator;
- Persistence Layer;
- Mission Data Manager;
- Observability.

### Sequence

For each suspicious site:

1. Gather:
   - accepted revisit images;
   - quality scores;
   - per-image health evidence;
   - per-image disease evidence;
   - source survey evidence;
   - revisit completion status.
2. Mission Orchestrator ⇢ Worker: `AggregateSiteEvidence`.
3. Aggregator:
   - rejects invalid evidence;
   - weights by quality;
   - calculates health agreement;
   - calculates disease agreement;
   - applies confidence policy;
   - withholds unsupported labels;
   - produces final site status.
4. Final result is persisted.
5. Aggregator ⇒ subscribers: `FinalSiteResultCreated`.

### Decision Examples

```text
unhealthy agreement
+ disease agreement
+ confidence sufficient
→ unhealthy_disease_identified
```

```text
unhealthy agreement
+ disease disagreement or low confidence
→ unhealthy_disease_uncertain
```

```text
revisit confirms healthy
→ healthy_after_suspicious_survey
```

```text
health remains uncertain
→ health_status_unresolved
→ manual_inspection_recommended
```

```text
revisit missing or unusable
→ revisit_not_completed
→ manual_inspection_recommended
```

### Persistence

```text
[DB] FinalSiteResult
[DB] AggregationMetrics
[ARTIFACT] final_site_results.csv
[EVENT] FinalSiteResultCreated
```

### Failure Behavior

- Preserve all per-image evidence.
- Mark site unresolved.
- Allow retry.
- Do not block safe return or landing.

### Next State

After safe flight completion and analysis readiness:

```text
return_to_home
```

or, if already landed:

```text
report_generation
```

# Part V — Return, Landing, Mapping, and Reporting

## 28. Flow 23 — Return Home

### Initial State

Usually:

```text
return_to_home
```

### Participants

- Mission Orchestrator;
- Safety Supervisor;
- Vehicle Adapter;
- PX4;
- Dashboard;
- Persistence Layer;
- Observability.

### Sequence

1. Mission Orchestrator transitions to `return_to_home`.
2. Mission Orchestrator → Vehicle Adapter: `ReturnHome`.
3. Vehicle Adapter → PX4: native return request.
4. Vehicle Adapter ⇒ subscribers: `ReturnHomeStarted`.
5. PX4 executes return.
6. Telemetry continues.
7. Vehicle Adapter ⇒ subscribers: `HomeReached`.
8. Mission Orchestrator transitions:

```text
return_to_home → landing
```

### Persistence

```text
[DB] ReturnHomeCommand
[DB] ReturnProgress
[EVENT] ReturnHomeStarted
[EVENT] HomeReached
[EVENT] MissionStateChanged
```

### Failure Behavior

- Return command rejected: Safety Supervisor selects land/hold/manual response.
- Link lost: PX4 native behavior remains authoritative.
- Manual takeover: application autonomy stops commands.

## 29. Flow 24 — Landing

### Initial State

```text
landing
```

### Participants

- PX4;
- Vehicle Adapter;
- Mission Orchestrator;
- Dashboard;
- Persistence Layer;
- Observability.

### Sequence

1. PX4 begins landing.
2. Vehicle Adapter ⇒ subscribers: `LandingStarted`.
3. PX4 reaches landed/disarmed condition.
4. Vehicle Adapter ⇒ subscribers: `VehicleLanded`.
5. Mission Orchestrator persists physical-flight completion.
6. Remaining data processing may continue.
7. Mission Orchestrator transitions:

```text
landing → report_generation
```

when required processing prerequisites are satisfied.

### Persistence

```text
[DB] LandingResult
[EVENT] LandingStarted
[EVENT] VehicleLanded
[EVENT] MissionStateChanged
```

### Failure Behavior

- Landing fails: operator/manual response and PX4 safety policy.
- Application never reports successful landing without telemetry evidence.

## 30. Flow 25 — Field Map Generation

### Initial State

```text
report_generation
```

### Participants

- Mission Orchestrator;
- Background Worker;
- Geospatial Mapper;
- Mission Data Manager;
- Persistence Layer;
- Artifact Storage;
- Observability.

### Sequence

1. Mission Orchestrator gathers:
   - boundary;
   - planned and actual routes;
   - telemetry;
   - observations;
   - suspicious sites;
   - revisit targets;
   - final results;
   - skipped areas.
2. Mission Orchestrator ⇢ Worker: `GenerateFieldMap`.
3. Geospatial Mapper generates:
   - field boundary;
   - flight path;
   - survey observations;
   - suspicious sites;
   - revisit targets;
   - final site results;
   - coverage geometry;
   - skipped-area geometry.
4. Artifacts are written atomically.
5. References are persisted.
6. Worker ⇒ subscribers: `FieldMapGenerated`.

### Persistence

```text
[ARTIFACT] field_boundary.geojson
[ARTIFACT] flight_path.geojson
[ARTIFACT] survey_observations.geojson
[ARTIFACT] suspicious_sites.geojson
[ARTIFACT] revisit_targets.geojson
[ARTIFACT] final_results.geojson
[ARTIFACT] field_map.html
[DB] MapArtifactReferences
[EVENT] FieldMapGenerated
```

### Failure Behavior

- Preserve structured results.
- Permit map regeneration.
- Do not alter final predictions.

## 31. Flow 26 — Report Generation

### Initial State

```text
report_generation
```

### Participants

- Mission Orchestrator;
- Background Worker;
- Report Generator;
- Mission Data Manager;
- Persistence Layer;
- Artifact Storage;
- Dashboard;
- Observability.

### Sequence

1. Mission Orchestrator gathers authoritative results and artifact references.
2. Mission Orchestrator ⇢ Worker: `GenerateReport`.
3. Report Generator produces:
   - mission summary;
   - surveyed coverage;
   - healthy/unhealthy/uncertain summary;
   - disease-identified sites;
   - unresolved sites;
   - skipped/failed revisit sites;
   - warnings/failures;
   - evidence links;
   - model/configuration traceability.
4. Report artifacts are written atomically.
5. References are persisted.
6. Worker ⇒ subscribers: `ReportGenerated`.
7. Mission Orchestrator verifies:
   - vehicle landed;
   - required final results persisted;
   - map/report status;
   - no unreconciled critical failure.
8. Mission Orchestrator transitions:

```text
report_generation → complete
```

9. Dashboard presents final map and report.

### Persistence

```text
[ARTIFACT] mission_summary.json
[ARTIFACT] report.html
[DB] ReportArtifactReferences
[EVENT] ReportGenerated
[EVENT] MissionStateChanged
```

### Failure Behavior

- Report failure does not discard results.
- Dashboard may expose raw structured results.
- Report job can retry without rerunning inference.
- Mission may remain `report_generation` until release policy is satisfied.

### Next State

```text
complete
```

# Part VI — Operator and Safety-Controlled Flows

## 32. Flow 27 — Operator Pause

### Possible States

```text
takeoff
survey
revisit
return_to_home
```

Pause availability depends on PX4 mode and safety policy.

### Sequence

1. Operator → Dashboard: pause request.
2. Dashboard → Mission API: `PauseMission`.
3. Mission API → Mission Orchestrator.
4. Mission Orchestrator validates current state.
5. Mission Orchestrator → Safety Supervisor: evaluate safe pause action.
6. Safety Supervisor returns hold/pause/reject.
7. Mission Orchestrator → Vehicle Adapter: hold/pause request.
8. Vehicle Adapter → PX4.
9. Vehicle Adapter ⇒ subscribers: `VehicleHoldConfirmed` or failure.
10. Mission Orchestrator records paused operational condition.

### Persistence

```text
[DB] OperatorCommand
[DB] PauseDecision
[EVENT] MissionPauseRequested
[EVENT] VehicleHoldConfirmed
```

### Failure Behavior

- Unsafe to hold: reject and explain safe alternative.
- Communication unavailable: PX4-native behavior controls.
- Pause does not imply mission cancellation.

### Resume Rule

Resume is a separate explicit command, not a background-job retry:

1. Operator → Dashboard: resume request.
2. Dashboard → Mission API: `ResumeMission`.
3. Mission Orchestrator verifies that the current mission created the confirmed vehicle hold and that no restart, authority loss, link-loss recovery, or manual takeover occurred.
4. Mission Orchestrator → Safety Supervisor: revalidate link, vehicle health, route, geofence, dry-daylight environment, battery, return, landing, and reserve.
5. Safety Supervisor returns `AUTHORIZED` or `REJECTED`.
6. On authorization, Mission Orchestrator records `MissionResumeAuthorized` and directs Vehicle Adapter to continue the remaining approved activity.
7. On rejection, the hold remains or Safety Supervisor selects return-home or controlled landing.

Resuming after process restart, lost authoritative context, or manual takeover is forbidden. Continued autonomous flight then requires a new recovery mission, technical preflight, and operator approval.

## 33. Flow 28 — Operator Abort

### Any Active State

Abort may be requested during any active mission stage.

### Sequence

1. Operator → Dashboard: abort.
2. Dashboard → Mission API: `AbortMission`.
3. Mission API → Mission Orchestrator.
4. Mission Orchestrator immediately records abort request.
5. Mission Orchestrator stops:
   - new route stages;
   - new capture scheduling;
   - new AI-generated flight requests.
6. Mission Orchestrator → Safety Supervisor: choose safe response.
7. Safety Supervisor normally returns:
   - return home;
   - land;
   - hold for manual intervention.
8. Mission Orchestrator → Vehicle Adapter with approved action.
9. Vehicle Adapter → PX4.
10. Partial evidence and checkpoints are preserved.
11. After safe flight termination, Mission Orchestrator transitions:

```text
active state → aborted
```

### Safety Meaning

Abort normally means cancel remaining work and safely return/land.

It does not mean emergency motor stop.

### Persistence

```text
[DB] AbortRequest
[DB] AbortSafetyDecision
[EVENT] MissionAbortRequested
[EVENT] ReturnHomeRequested or LandingRequested
[EVENT] MissionStateChanged
```

## 34. Flow 29 — Manual Takeover

### Sequence

1. Operator activates manual control.
2. PX4 prioritizes manual input.
3. Vehicle Adapter detects mode/control change.
4. Vehicle Adapter ⇒ subscribers: `ManualTakeoverDetected`.
5. Mission Orchestrator stops all new autonomous flight commands.
6. Safety Supervisor marks application autonomy unavailable.
7. Dashboard displays manual-control status.
8. Images, telemetry, and events remain preserved.
9. Mission becomes:
   - `aborted` after safe landing/termination;
   - or `failed` when policy requires;
   - never automatically resumed.

### Persistence

```text
[DB] ManualTakeoverRecord
[EVENT] ManualTakeoverDetected
[EVENT] MissionStateChanged
```

### Recovery

Any new autonomous flight requires a recovery mission, preflight, and approval.

# Part VII — Vehicle, Environment, and Capture Failures

## 35. Flow 30 — Low Battery

### Sequence

1. Vehicle Adapter emits updated battery telemetry.
2. Safety Supervisor detects threshold or feasibility change.
3. Safety Supervisor evaluates:
   - current location;
   - home distance;
   - remaining route;
   - landing energy;
   - reserve.
4. Safety Supervisor ⇒ Mission Orchestrator:
   - continue;
   - reduce revisit subset;
   - stop revisits;
   - return home immediately.
5. Mission Orchestrator stops unsafe future work.
6. Mission Orchestrator → Vehicle Adapter: approved return/land command.
7. Unvisited sites receive `revisit_skipped_battery`.
8. Partial evidence is preserved.

### Next State

Usually:

```text
return_to_home
```

### Native Safety

PX4-native battery failsafe remains authoritative and may act before application logic.

## 36. Flow 31 — GPS Degradation

### Sequence

1. Vehicle Adapter ⇒ subscribers: `VehicleHealthChanged(gps_degraded)`.
2. Safety Supervisor evaluates severity and current flight phase.
3. New route uploads and revisit start are blocked.
4. Depending on configured PX4 capability and conditions:
   - hold;
   - return;
   - land;
   - manual takeover.
5. Mission Orchestrator records unresolved work.
6. Geospatial confidence for affected images is marked degraded.

### Persistence

```text
[DB] GPSDegradationEvent
[DB] AffectedCaptureMetadata
[EVENT] VehicleHealthChanged
```

### Next State

Safety-dependent:

```text
return_to_home
landing
aborted
failed
```

## 37. Flow 32 — Telemetry-Link Loss

### Sequence

1. Vehicle Adapter detects stale/lost connection.
2. Vehicle Adapter ⇒ subscribers: `VehicleLinkLost`.
3. PX4 executes configured native link-loss behavior.
4. PlantGuard:
   - marks telemetry stale;
   - stops new vehicle commands;
   - preserves last known state;
   - alerts operator;
   - continues no safety-dependent application route progression.
5. If link returns:
   - Vehicle Adapter reconnects;
   - reads current PX4 state;
   - emits reconciliation event;
   - Mission Orchestrator does not assume prior state remained valid.
6. If flight ends under PX4/manual control, mission is reconciled and closed as aborted/failed/partial.

### Physical Resume Rule

Link restoration does not automatically resume the previous application mission.

## 38. Flow 33 — Camera Failure

### Single Capture Failure

1. Camera Manager emits `ImageCaptureFailed`.
2. Retry occurs only within policy and safe timing.
3. Failed capture remains recorded.

### Repeated or Complete Failure

1. Camera Manager marks camera unavailable.
2. Camera Manager ⇒ Mission Orchestrator and Safety Supervisor.
3. Mission Orchestrator stops new capture-dependent work.
4. Safety Supervisor normally recommends return home.
5. Vehicle Adapter executes approved return.
6. Existing images remain processable.
7. Uncaptured targets are marked unresolved.

### Next State

```text
return_to_home
```

or:

```text
aborted
```

after landing, depending on policy.

## 39. Flow 34 — Persistent Image-Quality Failure

### Sequence

1. Image Quality Validator rejects images with explicit reasons.
2. Worker aggregates quality metrics.
3. Mission Orchestrator compares rejection rate to policy.
4. During active flight, Safety Supervisor may recommend:
   - lower altitude within safe limits;
   - lower speed;
   - higher capture density;
   - camera check;
   - terminate inspection.
5. Any adaptive change requires route/safety validation.
6. Persistent failure triggers return home.
7. Rejected images remain in evidence manifests.

### Result Behavior

No field area is reported as healthy merely because its images were unusable.

# Part VIII — Perception and Runtime Failures

## 40. Flow 35 — Screening Failure

### Sequence

1. Screening worker/model emits failure.
2. Completed observations and checkpoints are preserved.
3. Mission Orchestrator disables AI-generated automatic revisit planning.
4. Safety Supervisor evaluates safe flight continuation.
5. The drone may:
   - finish already approved image collection;
   - return home;
   - land.
6. No suspicious-site completeness claim is made.
7. Processing can resume after landing.

### Next State

During flight:

```text
return_to_home
```

or continue capture only when safe and explicitly allowed.

After landing:

```text
initial_analysis
```

processing may resume from checkpoint.

## 41. Flow 36 — Disease-Classifier Failure

### Sequence

1. Disease classifier emits structured failure.
2. Revisit health evidence remains preserved.
3. Mission Orchestrator does not repeat flight solely to recover a software classifier immediately.
4. Sites with unhealthy evidence become:
   - `unhealthy_disease_uncertain`;
   - or `manual_inspection_recommended`.
5. Classifier job may resume later.
6. Safe return/landing continues independently.

### Important Distinction

Classifier failure does not invalidate captured revisit evidence.

## 42. Flow 37 — Worker Failure

### Sequence

1. Worker process crashes or becomes unhealthy.
2. Queue marks active job unacknowledged/failed according to implementation.
3. Checkpoints remain persisted.
4. Backend receives worker-health failure.
5. Mission Orchestrator stops scheduling new processing jobs.
6. Flight safety and vehicle commands remain available through backend and Vehicle Adapter.
7. Same-flight automatic revisit is disabled when required analysis is unavailable.
8. Worker restarts.
9. Retryable jobs resume from checkpoints.
10. Duplicate job effects are prevented by job ID/idempotency key.

### Physical Flight Rule

Worker restart never resumes physical flight.

## 43. Flow 38 — Model Runtime Failure

### Sequence

1. Runtime subprocess or library fails.
2. Worker catches/normalizes the failure.
3. Active model ID, version, inputs, and configuration are recorded.
4. Input artifacts remain unchanged.
5. Job is retried only according to policy.
6. No model output is fabricated.
7. Repeated failure marks job failed and site unresolved.

## 44. Flow 39 — Persistence Failure

### Sequence

1. Database operation fails.
2. Detecting component emits `PersistenceUnavailable`.
3. Mission Orchestrator stops:
   - new authoritative state transitions;
   - new unauditable decisions;
   - new reliable job submissions;
   - final result publication.
4. Temporary local buffering may continue only where explicitly safe.
5. Safety Supervisor evaluates return-home requirement.
6. Vehicle Adapter executes safe return/land where possible.
7. After recovery:
   - buffered events are reconciled;
   - duplicates are removed;
   - unresolved state is identified;
   - physical flight is not resumed.

### Next State

Usually:

```text
return_to_home
```

then:

```text
failed
```

or `aborted`, depending on cause and operator action.

## 45. Flow 40 — Artifact-Storage Failure

### Sequence

1. Artifact write fails or storage becomes unavailable.
2. Camera Manager/Mission Data Manager reports failure.
3. No incomplete artifact is marked complete.
4. Mission Orchestrator stops new evidence-dependent processing.
5. Continued capture is limited or stopped because evidence cannot be retained.
6. Safety Supervisor recommends return when storage cannot be restored.
7. Existing database references are marked pending/failed correctly.

### Important Rule

The system must not claim successful inspection when raw evidence could not be preserved.

## 46. Flow 41 — Weather Degradation

### Sequence

1. Operator or sensor input indicates degraded weather.
2. Safety Supervisor compares conditions with `nominal_dry_daylight`.
3. Safety Supervisor considers:
   - hardware weather rating;
   - VLOS;
   - image quality;
   - condensation risk;
   - wind;
   - obstacle clearance;
   - battery reserve.
4. No new survey or revisit work starts after an environmental-envelope violation.
5. Safety Supervisor selects return-home or controlled landing; PX4 failsafes and manual control remain authoritative.
6. Mission parameters are not changed merely to continue unsupported weather operation.
7. Weather decision is logged.

### Hard Block

Fog, mist, rain, precipitation, inadequate daylight, and degraded visibility are outside the production v1.0 envelope and cannot be authorized through runtime adaptation.

# Part IX — Restart, Resume, Reconciliation, and Recovery

## 47. Flow 42 — Interrupted Processing Resume

### Applies To

```text
image validation
screening
clustering
revisit reassessment
disease classification
aggregation
mapping
reporting
```

### Sequence

1. Worker/job interruption occurs.
2. Job record stores:
   - last completed unit;
   - checkpoint ID;
   - input snapshot;
   - model/configuration IDs;
   - failure reason.
3. After runtime recovery, operator/system issues `ResumeJob`.
4. Worker validates:
   - inputs still exist;
   - checkpoint is valid;
   - model/configuration contract is compatible;
   - job is retryable.
5. Worker resumes from the checkpoint.
6. Previously completed units are not repeated unless verification requires it.
7. Duplicate outputs are ignored or replaced atomically.
8. Completion event is emitted.

### Rule

This flow resumes data processing only.

It never resumes physical flight.

## 48. Flow 43 — Ground-Station Restart and Reconciliation

### Sequence

1. Ground station restarts.
2. Startup order verifies:
   - artifact storage;
   - database;
   - migrations;
   - logs;
   - models;
   - worker;
   - Vehicle Adapter;
   - backend;
   - dashboard.
3. Mission Orchestrator loads nonterminal missions.
4. Vehicle Adapter reconnects and reads current PX4 state.
5. Mission Orchestrator compares:
   - last persisted mission state;
   - latest event;
   - current PX4 mode;
   - landed/in-flight status;
   - available artifacts;
   - pending jobs.
6. Reconciliation outcome is recorded.
7. If the vehicle is still active:
   - application does not blindly continue;
   - PX4/manual control remains authoritative;
   - operator is alerted;
   - safe termination/recovery policy is applied.
8. If landed:
   - processing jobs may resume;
   - mission is marked interrupted/partial where appropriate.
9. Dashboard reconstructs its view.

### Prohibited Behavior

```text
restart backend
→ automatically upload previous route
→ automatically continue flight
```

is forbidden.

## 49. Flow 44 — Recovery-Mission Creation

### Initial Condition

A prior mission has unresolved:

- route segments;
- suspicious sites;
- revisit targets;
- captures;
- field regions.

### Sequence

1. Dashboard shows unresolved work from the source mission.
2. Operator selects a recovery objective.
3. Dashboard → Mission API: `CreateRecoveryMission`.
4. Mission Orchestrator creates a new mission ID.
5. New mission links to source mission.
6. Existing valid evidence is referenced, not duplicated unnecessarily.
7. Planner generates a new route for unresolved scope.
8. Safety Supervisor performs complete new validation.
9. Operator gives new takeoff approval.
10. Recovery mission proceeds independently.

### Persistence

```text
[DB] RecoveryMission
[DB] SourceMissionRelationship
[DB] RecoveryScope
[EVENT] RecoveryMissionCreated
```

### Rule

The old physical mission is never reactivated.

# Part X — State Transition Summary

## 50. Nominal State Path

```text
idle
→ preflight
→ awaiting_operator_approval
→ takeoff
→ survey
→ initial_analysis
→ revisit_planning
→ revisit
→ final_classification
→ return_to_home
→ landing
→ report_generation
→ complete
```

## 51. Nominal Path With No Suspicious Sites

```text
idle
→ preflight
→ awaiting_operator_approval
→ takeoff
→ survey
→ initial_analysis
→ return_to_home
→ landing
→ report_generation
→ complete
```

## 52. Post-Flight Processing Path

```text
idle
→ preflight
→ awaiting_operator_approval
→ takeoff
→ survey
→ return_to_home
→ landing
→ initial_analysis
→ report_generation
→ complete
```

Suspicious sites discovered after landing require a new recovery mission for revisit.

## 53. Abort Path

```text
any active state
→ return_to_home or landing
→ aborted
```

## 54. Unrecoverable Failure Path

```text
any active state
→ safe return/landing where possible
→ failed
```

## 55. Processing-Retry Path

```text
initial_analysis / final_classification / report_generation
→ job failure
→ checkpoint preserved
→ job resumed
→ same mission processing state continues
```

No physical flight continuation is implied.

# Part XI — Sequence Invariants

## 56. Mandatory Invariants

1. Dashboard never commands PX4 directly.
2. Mission Orchestrator owns mission-state changes.
3. Safety Supervisor approves or rejects flight actions.
4. Vehicle Adapter alone sends application commands to PX4.
5. PX4 retains native failsafes.
6. Manual takeover supersedes autonomy.
7. Models never command the aircraft.
8. Route planners never self-approve routes.
9. Route approval is current-state dependent.
10. Operator takeoff approval is recorded before takeoff.
11. Command acknowledgment is not completion.
12. Images are written atomically before being advertised as captured.
13. Rejected images do not enter normal inference.
14. Model failure never forces a prediction.
15. Partial evidence is preserved.
16. Persistence failure stops new unauditable decisions.
17. Worker failure does not destabilize flight.
18. Physical flight never resumes automatically.
19. Recovery flight uses a new mission.
20. Excluded areas are reported as uninspected.
21. Same-flight revisit occurs only when revisit, return, landing, and reserve remain feasible.
22. Unvisited or unusable sites remain visible in the final report.
23. Final site results remain traceable to evidence, models, and configuration.
24. Safe return/landing outranks analysis completion.
25. No flow requires cloud connectivity.

# Part XII — Frozen Flow Decisions

## 57. Frozen Decisions

1. Field selection remains non-mutating until mission creation.
2. Mission creation is authoritative only after persistence succeeds.
3. Accepted farmer route intent is persisted before planning.
4. Candidate routes are generated before safety validation.
5. Survey and revisit route approval are separate decisions.
6. Preflight is snapshot-based and may expire.
7. Operator approval is recorded before takeoff.
8. Takeoff acceptance and takeoff completion are separate.
9. Every planned capture has a logical capture ID.
10. Images are persisted before `ImageCaptured` is treated as complete.
11. Survey image validation precedes screening.
12. Screening results precede site clustering.
13. Site clustering precedes revisit planning.
14. Revisit planning precedes safety validation.
15. Same-flight revisit uses only the approved safe subset.
16. Revisit images are validated before reassessment.
17. Disease classification runs only on eligible unhealthy revisit evidence.
18. Multi-image aggregation owns final site results.
19. Safe return and landing do not wait for noncritical inference.
20. Mapping/reporting consume persisted truth.
21. Pause is distinct from abort.
22. Abort normally means safe return/landing, not motor stop.
23. Manual takeover ends application autonomy.
24. Low battery may reduce or cancel revisits.
25. GPS or link degradation blocks new flight actions.
26. Complete camera failure normally triggers return.
27. Persistent image-quality failure cannot be reported as healthy coverage.
28. Screening failure disables automatic AI revisit generation.
29. Classifier failure preserves unhealthy evidence and withholds disease.
30. Worker and model failures resume from processing checkpoints only.
31. Persistence failure stops new authoritative decisions.
32. Artifact-storage failure invalidates evidence-dependent mission continuation.
33. Weather adaptation requires new safety validation.
34. Restart reconciles state but does not resume flight.
35. Recovery flight always uses a new mission and approval.
36. Partial evidence and unresolved sites remain visible.
37. Every major flow emits audit events and preserves traceability.

# Part XIII — Sequence Acceptance Criteria

## 58. Acceptance Criteria

The mission-sequence baseline is complete when:

- field selection and mission creation are sequenced;
- route-intent and survey planning are sequenced;
- preflight and approval are sequenced;
- takeoff and survey are sequenced;
- capture, validation, and screening are sequenced;
- suspicious-site clustering is sequenced;
- revisit planning, approval, and execution are sequenced;
- revisit analysis and final aggregation are sequenced;
- return, landing, mapping, and reporting are sequenced;
- pause, abort, and manual takeover are sequenced;
- battery, GPS, link, camera, quality, weather, model, worker, persistence, and storage failures are sequenced;
- processing resume and ground-station reconciliation are sequenced;
- recovery-mission creation is sequenced;
- each flow identifies state, participants, messages, persistence, failures, and next state;
- no flow bypasses component ownership;
- partial evidence is preserved;
- physical flight never automatically resumes;
- the architecture is ready for end-to-end requirements traceability.

## 59. Final Sequence Statement

PlantGuard UAV v1.0 follows an explicit workflow in which:

```text
farmer intent
→ mission creation
→ route generation
→ safety validation
→ operator approval
→ PX4 flight execution
→ traceable image capture
→ quality validation
→ screening and site creation
→ safe revisit
→ evidence aggregation
→ return and landing
→ maps and reports
```

Every failure path preserves safe flight authority, honest mission state, partial evidence, unresolved work, and the separation between processing recovery and physical-flight recovery.
