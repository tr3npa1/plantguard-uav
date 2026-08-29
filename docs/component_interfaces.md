# PlantGuard UAV — Component Interfaces and Message Contracts

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Component Interfaces and Message Contracts |
| Target release | v1.0 |
| Status | Active architecture baseline |
| Related documents | `docs/system_architecture.md`, `docs/component_catalog.md`, `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md`, `docs/verification_and_acceptance_plan.md`, `docs/v1_scope_baseline.md` |
| Last updated | 2026-07-21 |

## 1. Document Purpose

This document defines how PlantGuard UAV v1.0 components communicate.

It freezes:

- interaction types;
- command, event, query, and job semantics;
- synchronous and asynchronous behavior;
- command acknowledgment versus physical completion;
- identifier and traceability requirements;
- idempotency rules;
- duplicate-delivery behavior;
- versioning rules;
- standard success, warning, rejection, and failure envelopes;
- component state-ownership boundaries;
- route-intent contracts;
- major mission, vehicle, camera, perception, revisit, reporting, failure, and recovery contracts.

This document does not define exact Python class names, FastAPI paths, database schemas, queue technology, serialization libraries, network transports, or source-file structure. Those implementation decisions are made later, but they must preserve the semantics defined here.

## 2. Interface Design Principles

### 2.1 One Message, One Meaning

Every message represents one clear intent or one clear fact. A message must not simultaneously act as a command and an event, a query and a mutation, or a job request and a completion result.

### 2.2 Commands Request Actions

A command asks a component to perform an action.

```text
CreateMission
ApproveTakeoff
GenerateSurveyPlan
CaptureImage
AbortMission
ReturnHome
```

A command describes intent, not a completed fact.

### 2.3 Events Describe Facts

An event states that something already happened or was observed.

```text
MissionCreated
TakeoffCompleted
ImageCaptured
ScreeningCompleted
MissionStateChanged
VehicleLanded
```

Events are immutable facts and must not be used to request work.

### 2.4 Queries Read Without Mutating

A query requests current or historical information.

```text
GetMissionStatus
GetFieldDefinition
GetRoutePreview
GetFinalSiteResults
```

Queries must not change domain state.

### 2.5 Jobs Represent Long-Running Work

A job requests asynchronous work that may require progress, retries, checkpointing, cancellation, resource scheduling, or delayed completion.

```text
ValidateMissionImages
ScreenSurveyImages
ClusterSuspiciousObservations
ClassifyRevisitImages
GenerateMissionReport
```

### 2.6 Acceptance Is Not Completion

```text
ReturnHome accepted
≠
Vehicle returned home
≠
Vehicle landed
```

Completion is reported separately through an event or job result.

### 2.7 State Owners Mutate Their Own State

A component may request another component to change state, but must not directly mutate another component’s owned state.

```text
Safety Supervisor
→ returns TakeoffApproved

Mission Orchestrator
→ owns the mission-state transition
```

### 2.8 Large Artifacts Move by Reference

Control messages do not contain full-resolution images, model files, or large reports. They carry stable artifact references.

### 2.9 Retry Safety Is Mandatory

Every retryable command, event consumer, and job defines duplicate-delivery behavior.

### 2.10 Traceability Is Mandatory

Every meaningful interaction is traceable to the relevant field, mission, route, image, observation, site, model, configuration, job, and causal message.

## 3. Interaction Types

## 3.1 Command

A command requests a state-changing action.

Required characteristics:

- imperative name;
- one intended receiver;
- clear authorization;
- idempotency behavior;
- acknowledgment result;
- structured rejection;
- no assumption of completion.

## 3.2 Event

An event records a completed or observed fact.

Required characteristics:

- past-tense or fact-oriented name;
- immutable payload;
- event timestamp;
- producing component;
- source entity;
- duplicate-safe consumption.

## 3.3 Query

A query retrieves information.

Required characteristics:

- no domain-state mutation;
- no side effects beyond metrics;
- explicit not-found response;
- pagination where applicable.

## 3.4 Job

A job requests long-running asynchronous work.

Required characteristics:

- unique `job_id`;
- job type;
- idempotency key;
- status;
- progress;
- retry policy;
- checkpoint;
- failure details;
- completion event.

## 4. Communication Styles

### 4.1 Synchronous Request/Response

Use synchronous request/response for bounded operations that need immediate acceptance, rejection, or current-state answers.

```text
CreateMission
SubmitRouteIntent
RunPreflight
ApproveTakeoff
PauseMission
ResumeMission
AbortMission
ReturnHome
GetMissionStatus
GetRoutePreview
```

Synchronous responses do not wait for inference or physical flight completion.

### 4.2 Asynchronous Event Delivery

Use events for state changes, physical completion, telemetry observations, processing completion, failures, and audit history.

### 4.3 Asynchronous Jobs

Use jobs for bulk image validation, screening, clustering, revisit analysis, disease classification, aggregation, map generation, report generation, and reprocessing.

### 4.4 Streaming or Periodic Updates

Telemetry and job progress may use streaming or periodic event delivery. High-frequency raw telemetry may be downsampled before persistence and dashboard delivery.

## 5. Standard Message Metadata

| Field | Purpose |
|---|---|
| `message_id` | Unique message identifier |
| `schema_version` | Contract version |
| `created_at` | UTC creation timestamp |
| `producer` | Producing component |
| `correlation_id` | Groups one higher-level operation |
| `causation_id` | Identifies the causing message |
| `idempotency_key` | Prevents duplicate effects |
| `field_id` | Field context |
| `mission_id` | Mission context |
| `route_id` | Route context |
| `image_id` | Image context |
| `observation_id` | Observation context |
| `site_id` | Suspicious-site context |
| `job_id` | Job context |
| `model_id` | Model identity |
| `model_version` | Model version |
| `configuration_id` | Configuration snapshot |
| `actor_id` | Authorized user/operator |
| `trace_id` | Trace correlation |
| `priority` | Operational or processing priority |

Identifiers must be unique, immutable, opaque to clients, safe for persistence, and never reused. Persisted timestamps use UTC.

## 6. Standard Command Envelope

```json
{
  "message_id": "msg_01",
  "schema_version": "1.0",
  "created_at": "2026-07-21T12:00:00Z",
  "producer": "farmer_dashboard",
  "correlation_id": "corr_01",
  "causation_id": null,
  "idempotency_key": "mission-create-operator-42-20260721",
  "actor_id": "operator_42",
  "mission_id": null,
  "payload": {}
}
```

## 7. Standard Acknowledgment Envelopes

### Accepted

```json
{
  "status": "accepted",
  "message_id": "msg_01",
  "correlation_id": "corr_01",
  "accepted_at": "2026-07-21T12:00:01Z",
  "result": {},
  "warnings": []
}
```

### Accepted With Warnings

```json
{
  "status": "accepted_with_warnings",
  "message_id": "msg_01",
  "correlation_id": "corr_01",
  "accepted_at": "2026-07-21T12:00:01Z",
  "result": {},
  "warnings": [
    {
      "code": "coverage_reduced_by_exclusion_zone",
      "message": "Final field-health percentages will describe only the surveyed region."
    }
  ]
}
```

### Rejected

```json
{
  "status": "rejected",
  "message_id": "msg_01",
  "correlation_id": "corr_01",
  "rejected_at": "2026-07-21T12:00:01Z",
  "error": {
    "code": "route_outside_geofence",
    "message": "The candidate route leaves the approved field boundary.",
    "retryable": false,
    "details": {}
  }
}
```

### Failed During Handling

```json
{
  "status": "failed",
  "message_id": "msg_01",
  "correlation_id": "corr_01",
  "failed_at": "2026-07-21T12:00:01Z",
  "error": {
    "code": "persistence_unavailable",
    "message": "The command could not be recorded safely.",
    "retryable": true,
    "details": {}
  }
}
```

## 8. Standard Event Envelope

```json
{
  "message_id": "evt_01",
  "schema_version": "1.0",
  "created_at": "2026-07-21T12:00:10Z",
  "producer": "px4_mavsdk_vehicle_adapter",
  "correlation_id": "corr_01",
  "causation_id": "msg_takeoff_01",
  "mission_id": "mission_01",
  "event_type": "TakeoffCompleted",
  "payload": {}
}
```

Events are immutable. Corrections use a new event.

## 9. Standard Job Envelopes

### Job Accepted

```json
{
  "status": "accepted",
  "job_id": "job_01",
  "job_type": "ScreenSurveyImages",
  "correlation_id": "corr_01",
  "mission_id": "mission_01",
  "checkpoint_supported": true
}
```

### Job Progress

```json
{
  "event_type": "JobProgressUpdated",
  "job_id": "job_01",
  "mission_id": "mission_01",
  "completed_units": 84,
  "total_units": 120,
  "progress_fraction": 0.7,
  "checkpoint_id": "checkpoint_07"
}
```

### Job Completed

```json
{
  "event_type": "JobCompleted",
  "job_id": "job_01",
  "mission_id": "mission_01",
  "result_reference": "artifact://mission_01/screening/results.json"
}
```

### Job Failed

```json
{
  "event_type": "JobFailed",
  "job_id": "job_01",
  "mission_id": "mission_01",
  "error": {
    "code": "model_runtime_failure",
    "message": "The screening runtime terminated unexpectedly.",
    "retryable": true
  },
  "checkpoint_id": "checkpoint_07"
}
```

## 10. Error Model

Every failure or rejection provides:

| Field | Meaning |
|---|---|
| `code` | Stable machine-readable reason |
| `message` | Human-readable explanation |
| `retryable` | Whether retry is valid |
| `details` | Supporting structured context |
| `source_component` | Detecting component |
| `occurred_at` | UTC timestamp |
| `related_artifact_ids` | Associated evidence |
| `recommended_action` | Optional safe next step |

Error categories:

```text
validation_error
authorization_error
safety_rejection
state_conflict
not_found
dependency_unavailable
hardware_failure
model_failure
data_quality_failure
persistence_failure
timeout
cancellation
unsupported_operation
internal_error
```

Existing domain reason codes remain valid:

```text
insufficient_visual_resolution
image_too_blurry
image_underexposed
image_overexposed
lens_obstructed
plant_region_too_small
plant_not_visible
health_confidence_too_low
disease_confidence_too_low
disease_classification_uncertain
top_predictions_too_similar
inconsistent_revisit_views
unsupported_crop
unsupported_condition
revisit_capture_failed
revisit_skipped_safety
revisit_skipped_battery
revisit_skipped_route_invalid
revisit_skipped_weather
manual_inspection_recommended
```

## 11. Idempotency Rules

### Command Idempotency

Retryable commands include an `idempotency_key`. Duplicate commands with the same key and equivalent payload return the original result. A reused key with a conflicting payload is rejected.

### Event Idempotency

Consumers recognize processed `message_id` values. Duplicate events must not create duplicate records, repeat commands, increment counters twice, create duplicate sites, or duplicate report sections.

### Job Idempotency

A duplicate logical job returns the existing active job, completed result, or linked retry attempt according to policy.

### Safety-Critical Idempotency

```text
ApproveTakeoff
Takeoff
UploadRoute
AbortMission
ReturnHome
Land
```

must be safe under retries, lost acknowledgments, and duplicate delivery.

## 12. Versioning Rules

Every persisted or transmitted contract includes `schema_version`, initially:

```text
1.0
```

Compatible changes may add optional fields. Removing fields, changing meaning, units, requiredness, identifiers, or state ownership requires a new major version.

Unknown safety-critical enum values are rejected safely. Unknown optional non-safety fields may be ignored.

## 13. State Ownership

| State | Owner |
|---|---|
| Mission workflow state and activity | Mission Orchestrator |
| Vehicle operational state | PX4 through Vehicle Adapter |
| Application safety decision | Safety Supervisor |
| Vehicle connection and telemetry | Vehicle Adapter |
| Candidate survey route | Survey Planner |
| Candidate revisit route | Revisit Planner |
| Camera state | Camera Manager |
| Image quality result | Image Quality Validator |
| Survey observation | Aerial Health Screening Service |
| Suspicious site | Suspicious-Site Clusterer |
| Revisit health evidence | Revisit Health Reassessment Service |
| Disease evidence | PlantGuard Disease Classifier |
| Final site result | Multi-Image Result Aggregator |
| Structured records | Persistence Layer |
| Artifact relationships | Mission Data Manager |
| Model contract | Model Registry and Metadata Manager |
| Processing-job state | Background Job Worker |
| Audit event | Observability and Event Logger |

No component directly mutates another owner’s state.

## 14. Canonical State Dimensions

### Mission Workflow State

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

Only the Mission Orchestrator owns workflow-state transitions.

### Mission Activity

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

### Vehicle Operational State

```text
unknown
disconnected
on_ground
armed
taking_off
in_flight
holding
returning_home
landing
landed
manual_control
```

### Processing Job State

```text
queued
running
retry_wait
paused
succeeded
failed
cancelled
```

Vehicle state is derived from PX4 through the Vehicle Adapter. Processing state is owned by the Background Job Worker. Neither may be mutated through `TransitionMissionState`.

## 15. Canonical Final Site Statuses

```text
healthy
healthy_after_suspicious_survey
unhealthy_disease_identified
unhealthy_disease_uncertain
health_status_unresolved
manual_inspection_recommended
revisit_not_completed
```

`revisit_capture_failed` is emitted only as a reason code attached to `revisit_not_completed`. `manual_inspection_recommended`, `health_status_unresolved`, `unhealthy_disease_uncertain`, and `revisit_not_completed` are explicit action-required or unresolved outcomes and do not count as automatically resolved sites.

## 16. Route-Intent Contracts

### SubmitRouteIntent Command

Sender: Farmer Dashboard.

Receiver: Mission API and application handling.

Payload:

```json
{
  "field_id": "field_01",
  "sector_id": "sector_01",
  "mission_id": "mission_01",
  "mode": "automatic_coverage",
  "exclusion_zones": []
}
```

The only allowed v1.0 mode is:

```text
automatic_coverage
```

Sweep direction, altitude, speed, overlap, and coverage density come from versioned, safety-reviewed mission configuration. Priority zones, guided modes, and custom route drafts are rejected as unsupported v1.0 inputs.

Result: accepted, accepted with warnings, or rejected malformed input.

The dashboard owns unsaved editing state. Accepted route intent becomes persisted mission configuration.

### GenerateSurveyPlan Command

Sender: Mission Orchestrator.

Receiver: Survey Planner.

Input:

- field boundary;
- route intent;
- home position;
- camera geometry;
- operating limits;
- configuration ID.

Output:

```text
route_id
candidate waypoints
capture points
coverage estimate
skipped-area geometry
estimated distance
estimated duration
warnings
```

Equivalent geometry, intent, and configuration produce the same logical plan version.

### SurveyPlanGenerated Event

Produced by Survey Planner. Consumed by Mission Orchestrator, Safety Supervisor, Mission Data Manager, Dashboard read model, and Observability.

It means a candidate route exists, not that it is approved.

### ValidateSurveyPlan Command

Sender: Mission Orchestrator.

Receiver: Safety Supervisor.

Result:

```text
approved
approved_with_restrictions
rejected
```

Restrictions may include reduced speed, higher reserve, removed segments, reduced scope, or extra warnings.

## 17. Field and Mission Setup Contracts

### SelectField Command

Sender: Dashboard.

Receiver: Mission API.

Repeated selection has no additional effect.

### GetFieldDefinition Query

Returns field boundary, exclusions, home location, saved metadata, and version. It performs no mutation.

### CreateMission Command

Payload includes field ID, mission profile, route intent, operator ID, and requested model/configuration profile.

Result includes mission ID, initial state, and configuration snapshot reference.

A duplicate request returns the existing mission.

### MissionCreated Event

Produced only after authoritative persistence succeeds.

## 18. Preflight and Approval Contracts

### RunPreflight Command

Sender: Mission Orchestrator.

Receiver: Safety Supervisor.

Input includes mission ID, route ID, vehicle state, camera/model/storage readiness, production-environment checks, operator-supervision readiness, and configuration ID. Missing takeoff approval is not a technical-preflight check.

Result:

```text
PASS
WARNING
BLOCKED
```

with structured checks and reasons.

Preflight is versioned by its input snapshot. Changed telemetry or configuration requires a new result.

### PreflightCompleted Event

Contains outcome, checks, warnings, blockers, expiry conditions, and source snapshot IDs.

### ApproveTakeoff Command

Sender: Dashboard through Mission API.

Receiver: Mission Orchestrator.

Preconditions:

- mission state is `awaiting_operator_approval`;
- valid preflight exists;
- actor is authorized;
- route is approved;
- no new blocker exists.

The response acknowledges approval handling; takeoff completion is separate.

### TakeoffApprovalRecorded Event

Records operator approval. It does not mean takeoff began.

### ValidateTakeoffAuthorization Command

Sender: Mission Orchestrator.

Receiver: Safety Supervisor.

Preconditions:

- valid technical-preflight snapshot exists and is not expired;
- approval is recorded by an authorized actor and references that snapshot;
- route and configuration versions still match;
- latest telemetry contains no new blocker;
- vehicle remains disarmed until validation succeeds.

Result is `AUTHORIZED` or `REJECTED` with structured reasons. Rejection invalidates readiness and returns the workflow to `preparing`; authorization permits transition to `ready` and issuance of one idempotent takeoff command.

Completion event: `TakeoffAuthorizationValidated`.

## 19. Mission-State Contracts

### TransitionMissionState Operation

Only the Mission Orchestrator may perform authoritative state transitions.

Required data:

- mission ID;
- previous workflow state;
- next workflow state;
- causation message;
- reason;
- timestamp.

Invalid transitions are rejected.

### MissionStateChanged Event

Contains previous workflow state, new workflow state, reason, triggering message, current mission activity, vehicle-state snapshot reference, and warnings.

## 20. Vehicle Contracts

### ConnectVehicle Command

Completion events:

```text
VehicleConnected
VehicleConnectionFailed
```

### UploadRoute Command

Preconditions:

- route approved;
- approval reference included;
- mission state permits upload.

Completion events:

```text
RouteUploaded
RouteUploadFailed
```

### Takeoff Command

Preconditions:

- operator approval recorded;
- final takeoff authorization valid;
- workflow state is `ready`;
- vehicle ready.

Completion events:

```text
TakeoffStarted
TakeoffCompleted
TakeoffFailed
```

Duplicate delivery must not produce repeated takeoff behavior.

### StartSurvey Command

Completion events:

```text
SurveyStarted
SurveyProgressUpdated
SurveyCompleted
SurveyFailed
```

### PauseMission Command

Pause is a request for a safety-evaluated vehicle hold; it is not a guaranteed command and does not change the mission into a resumable background job.

Completion events:

```text
MissionPauseRequested
VehicleHoldConfirmed
MissionPaused
MissionPauseFailed
```

If holding would violate link, energy, geofence, weather, or PX4 constraints, the request is rejected or converted by the Safety Supervisor into return-home or controlled landing.

### ResumeMission Command

Sender: Dashboard through Mission API.

Receiver: Mission Orchestrator.

Preconditions:

- the vehicle is in a confirmed hold created by the current mission;
- the operator explicitly requests resume;
- link, vehicle, route, geofence, environment, battery, return, landing, and reserve checks pass again;
- no process restart, authority loss, manual takeover, or link-loss recovery occurred;
- the remaining approved activity is still valid.

Completion events:

```text
MissionResumeRequested
MissionResumeAuthorized
MissionResumed
MissionResumeRejected
```

A process restart, manual takeover, or loss of authoritative mission context makes `ResumeMission` invalid. Continued autonomous flight then requires a new recovery mission, technical preflight, and operator approval.

### AbortMission Command

Cancels remaining work and normally initiates safe return or landing. It does not mean motor stop.

Completion events:

```text
MissionAbortRequested
ReturnHomeRequested
MissionAborted
```

### ReturnHome Command

Completion events:

```text
ReturnHomeStarted
HomeReached
LandingStarted
VehicleLanded
ReturnHomeFailed
```

### Land Command

Completion events:

```text
LandingStarted
VehicleLanded
LandingFailed
```

## 21. Telemetry Contracts

### TelemetryUpdated Event

Producer: Vehicle Adapter.

Payload may include UTC and monotonic timestamps, WGS 84 longitude/latitude, explicit AGL and AMSL altitude fields, coordinate/frame references, uncertainty, velocity, heading, battery, GPS health, flight mode, home position, and link quality. Generic unlabeled `altitude` fields are forbidden.

Consumers: Safety Supervisor, Mission Orchestrator, Camera Manager, telemetry persistence, and Dashboard read model.

High-rate telemetry may be downsampled, but safety changes and capture-linked snapshots must be preserved.

### VehicleHealthChanged Event

Examples:

```text
gps_degraded
battery_low
link_degraded
manual_control_active
vehicle_not_armable
```

### ManualTakeoverDetected Event

Application autonomy stops issuing new flight commands. The Mission Orchestrator and Safety Supervisor handle state and safety response.

## 22. Camera Contracts

### CaptureImage Command

Payload includes mission ID, capture stage, route/waypoint reference, optional site ID, telemetry snapshot, capture policy, and retry limit.

Completion events:

```text
ImageCaptured
ImageCaptureFailed
```

A unique logical capture ID prevents duplicate records. A retry creates a new physical image only when policy permits.

### ImageCaptured Event

Contains image ID, artifact reference, stage, UTC timestamp, monotonic capture timestamp, camera metadata, synchronized telemetry/pose snapshot, coordinate and altitude references, uncertainty, route context, and optional site ID. Inputs outside the configured synchronization or pose-uncertainty limit are rejected for geospatial decisions.

### ImageCaptureFailed Event

Contains capture request ID, reason, retry count, retryability, and site/waypoint context.

## 23. Image-Quality Contracts

### ValidateImage Job

Input:

- image reference;
- image metadata;
- quality configuration ID.

Completion events:

```text
ImageAccepted
ImageRejected
ImageValidationFailed
```

### ImageAccepted Event

Contains image ID, quality score, validator version, accepted checks, and downstream eligibility.

### ImageRejected Event

Contains image ID, quality score, reason codes, and retry/revisit recommendation where applicable.

Rejected images do not enter normal inference.

## 24. Survey Screening Contracts

### ScreenSurveyImages Job

Input:

- accepted survey images;
- model contract ID;
- confidence policy ID;
- configuration ID.

Completion events:

```text
SurveyScreeningStarted
SurveyImageScreened
SurveyScreeningCompleted
SurveyScreeningFailed
```

### SurveyImageScreened Event

Contains image ID, observation IDs, counts by status, model/preprocessing version, and timing.

### Screening Observation Contract

Each observation includes observation ID, image ID, mission ID, region reference, health status, confidence, geographic context, model metadata, timestamp, and source tile where applicable.

Allowed health statuses:

```text
healthy
unhealthy
uncertain
```

## 25. Suspicious-Site Contracts

### ClusterSuspiciousObservations Job

Input:

- unhealthy observations;
- uncertain observations;
- geospatial metadata;
- clustering configuration.

Completion events:

```text
SuspiciousSiteCreated
SuspiciousSiteUpdated
SuspiciousSiteClusteringCompleted
SuspiciousSiteClusteringFailed
```

### SuspiciousSiteCreated Event

Contains site ID, representative location, supporting observation IDs, evidence summary, clustering configuration, and priority evidence.

Duplicate observations must not be appended twice.

## 26. Revisit-Planning Contracts

### GenerateRevisitPlan Command or Job

Input:

- eligible suspicious sites;
- priority policy;
- field/exclusion geometry;
- home position;
- revisit configuration;
- time/energy budget context.

Output:

- candidate route;
- ordered targets;
- skipped sites;
- distance/duration estimate;
- route ID.

Completion event:

```text
RevisitPlanGenerated
```

### ValidateRevisitPlan Command

Result:

- approved;
- approved with restrictions;
- rejected;
- approved safe subset.

Required skip codes:

```text
revisit_skipped_safety
revisit_skipped_battery
revisit_skipped_route_invalid
revisit_skipped_weather
```

### RevisitPlanApproved Event

Records the safety decision and approved target subset.

## 27. Revisit-Execution Contracts

### StartRevisit Command

Preconditions:

- approved revisit route;
- mission state `revisit`;
- current safety approval;
- original authorization policy permits automatic revisit continuation.

Completion events:

```text
RevisitStarted
RevisitTargetReached
RevisitTargetCompleted
RevisitTargetFailed
RevisitCompleted
RevisitFailed
```

### RevisitTargetCompleted Event

Contains site ID, target ID, captured image IDs, arrival telemetry, and completion time.

### RevisitTargetFailed Event

Contains site ID, reason, retryability, partial evidence, and route-continuation decision.

## 28. Revisit Health Contracts

### ReassessRevisitHealth Job

Input:

- accepted revisit images;
- site ID;
- model contract ID;
- confidence policy.

Completion events:

```text
RevisitImageHealthAssessed
RevisitHealthAssessmentCompleted
RevisitHealthAssessmentFailed
```

### RevisitImageHealthAssessed Event

Contains image ID, site ID, health status, confidence, model metadata, and timing.

## 29. Disease Classification Contracts

### ClassifyDisease Job

Preconditions:

- accepted revisit image;
- unhealthy health evidence;
- supported crop/condition;
- valid model contract.

Input includes image reference, site ID, health-evidence reference, model contract, and policy.

Completion events:

```text
DiseaseImageClassified
DiseaseClassificationCompleted
DiseaseClassificationFailed
```

### DiseaseImageClassified Event

Contains image ID, site ID, top-k predictions, confidences, supported/unsupported status, model metadata, and timing.

## 30. Multi-Image Aggregation Contracts

### AggregateSiteEvidence Job

Input:

- site ID;
- image-quality results;
- per-image health results;
- per-image disease evidence;
- aggregation policy;
- model/configuration snapshots.

Completion events:

```text
FinalSiteResultCreated
SiteEvidenceAggregationFailed
```

### FinalSiteResultCreated Event

Contains site ID, final status, optional disease label, confidence, reasons, evidence image IDs, per-image references, agreement metrics, and model/configuration references.

## 31. Geospatial Contracts

### GenerateFieldMap Job

Input:

- field geometry;
- route and telemetry;
- observations;
- sites;
- revisit targets;
- final results.

Output:

- GeoJSON references;
- coverage metrics;
- map layers;
- skipped-area geometry;
- geospatial error metadata.

Completion events:

```text
FieldMapGenerated
FieldMapGenerationFailed
```

### GetFieldMap Query

Returns existing map references and metadata. It does not regenerate the map.

## 32. Report Contracts

### GenerateReport Job

Input:

- mission summary;
- final results;
- maps;
- evidence;
- warnings/failures;
- metrics;
- configuration snapshot.

Output:

- HTML report reference;
- machine-readable summary;
- report metadata.

Completion events:

```text
ReportGenerated
ReportGenerationFailed
```

### GetReportStatus Query

Returns pending, running, complete, or failed status, artifact references, and failure details.

## 33. Background-Job Control Contracts

### StartJob Command

Includes job type, mission ID, input references, idempotency key, retry policy, resource class, and priority.

### CancelJob Command

Cancellation is allowed only when safe. Physical-flight control is never represented as a cancellable background job.

### ResumeJob Command

Requires a paused or failed retryable job, valid checkpoint, available inputs, and permitted retry policy.

## 34. Recovery-Mission Contracts

### CreateRecoveryMission Command

Preconditions:

- previous mission interrupted;
- source mission recorded;
- recovery scope selected;
- new preflight required;
- new operator approval required.

Input includes source mission ID, unresolved sites or route segments, retained evidence, and recovery objective.

Output includes new mission ID, source link, recovery scope, and initial state.

Duplicate requests must not create multiple recovery missions.

### RecoveryMissionCreated Event

Records the new independent mission. Physical flight is never resumed by reactivating the old mission.

## 35. Failure Propagation Rules

A failing component reports failure to its caller or orchestrator, Observability and Event Logger, and Persistence Layer where an authoritative record is required.

Safety-relevant failures are sent to Mission Orchestrator, Safety Supervisor, Dashboard warning view, and Observability.

Only Mission Orchestrator changes mission state. Only Safety Supervisor owns application safety decisions. Only Vehicle Adapter executes approved vehicle actions.

Model failure preserves source evidence, produces no forced prediction, records model/configuration identity, and routes to unresolved or manual-inspection handling.

Persistence failure stops new unauditable decisions, attempts safe local buffering, escalates immediately, and favors return-home when mission integrity cannot be maintained.

## 36. Major Interaction Matrix

| Interaction | Type | Sender | Receiver | Completion |
|---|---|---|---|---|
| Select field | Command | Dashboard | Mission API | Immediate |
| Create mission | Command | Dashboard/API | Mission Orchestrator | `MissionCreated` |
| Submit route intent | Command | Dashboard | Mission API/Application | Immediate |
| Generate survey plan | Command/Job | Orchestrator | Survey Planner | `SurveyPlanGenerated` |
| Validate survey plan | Command | Orchestrator | Safety Supervisor | Immediate |
| Run preflight | Command | Orchestrator | Safety Supervisor | `PreflightCompleted` |
| Approve takeoff | Command | Dashboard | Orchestrator | Approval recorded |
| Validate takeoff authorization | Command | Orchestrator | Safety Supervisor | `TakeoffAuthorizationValidated` |
| Take off | Command | Orchestrator | Vehicle Adapter | `TakeoffCompleted` |
| Start survey | Command | Orchestrator | Vehicle Adapter | `SurveyCompleted` |
| Publish telemetry | Event | Vehicle Adapter | Subscribers | Continuous |
| Capture image | Command | Capture workflow | Camera Manager | `ImageCaptured` |
| Validate image | Job | Orchestrator | Worker/Validator | Validation events |
| Screen images | Job | Orchestrator | Worker/Screening | Screening events |
| Cluster sites | Job | Orchestrator | Worker/Clusterer | Site events |
| Generate revisit plan | Command/Job | Orchestrator | Revisit Planner | Plan event |
| Validate revisit plan | Command | Orchestrator | Safety Supervisor | Immediate |
| Start revisit | Command | Orchestrator | Vehicle Adapter | Revisit events |
| Reassess health | Job | Orchestrator | Worker/Reassessment | Health events |
| Classify disease | Job | Analysis workflow | Worker/Classifier | Disease events |
| Aggregate evidence | Job | Orchestrator | Worker/Aggregator | Final result |
| Return home | Command | Orchestrator | Vehicle Adapter | `VehicleLanded` |
| Generate map | Job | Orchestrator | Worker/Mapper | Map event |
| Generate report | Job | Orchestrator | Worker/Reporter | Report event |
| Abort mission | Command | Dashboard/Safety path | Orchestrator | Abort/return events |
| Pause mission | Command | Dashboard | Orchestrator | Hold/pause events |
| Resume held mission | Command | Dashboard | Orchestrator | Resume/rejection events |
| Resume processing | Command | Operator/System | Worker | Job events |
| Create recovery mission | Command | Dashboard | Orchestrator | Recovery event |

## 37. Forbidden Interaction Patterns

```text
Dashboard → Vehicle Adapter directly
Dashboard → PX4 directly
Model Service → Vehicle Adapter
Model Service → mission-state mutation
Planner → vehicle execution
Planner → route self-approval
Safety Supervisor → direct mission-state mutation
Persistence Layer → product-policy decision
Report Generator → final-result reinterpretation
Worker → workflow-state ownership
Event Logger → operational decision
```

## 38. Frozen Interface Decisions

1. Commands request actions.
2. Events describe completed or observed facts.
3. Queries read without mutating state.
4. Long-running processing uses jobs.
5. Acceptance is separate from completion.
6. Every retryable command uses an idempotency key.
7. Every event consumer is duplicate-safe.
8. Jobs support status, progress, failure details, and checkpoints where applicable.
9. Major messages carry sufficient mission and evidence identifiers.
10. Components never directly mutate another component’s owned state.
11. Mission Orchestrator alone owns mission-state transitions.
12. Safety Supervisor returns decisions but does not execute vehicle commands.
13. Vehicle Adapter receives only validated flight commands.
14. Dashboard route input is route intent, not executable waypoints.
15. Large artifacts move by reference.
16. Persisted and transmitted messages are versioned.
17. Failures use stable codes and retryability information.
18. Physical-flight commands define duplicate-delivery behavior.
19. Telemetry may be downsampled, but safety changes and capture-linked snapshots are preserved.
20. Physical flight cannot be resumed through a job retry.
21. Recovery flight requires a new mission, preflight, and operator approval.
22. Model failure never forces a prediction.
23. Persistence failure stops new unauditable decisions.
24. Events are immutable; corrections use new events.
25. Unknown safety-critical contract values are rejected safely.

## 39. Interface-Contract Acceptance Criteria

The interface-contract baseline is complete when:

- command, event, query, and job semantics are explicit;
- synchronous and asynchronous behavior are explicit;
- acknowledgment and completion are separated;
- identifiers are defined;
- idempotency and duplicate delivery are defined;
- versioning is defined;
- result/error envelopes are defined;
- state ownership is explicit;
- route-intent contracts are explicit;
- every major interaction has sender, receiver, payload, result, failure, and retry behavior;
- safety and workflow ownership cannot be bypassed;
- the document is ready for runtime and deployment architecture design.

## 40. Final Interface Statement

PlantGuard UAV v1.0 communicates through explicit, traceable, versioned contracts in which:

```text
commands request work
events record facts
queries read state
jobs perform long-running processing
```

The architecture prevents direct cross-component state mutation, separates acceptance from completion, preserves retry safety, and maintains traceability from farmer intent through flight, imagery, inference, revisit, final results, mapping, and reporting.
