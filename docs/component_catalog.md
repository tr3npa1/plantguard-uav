# PlantGuard UAV — Component Catalog

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Component Catalog |
| Target release | v1.0 |
| Status | Active architecture baseline |
| Related documents | `docs/system_architecture.md`, `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md`, `docs/verification_and_acceptance_plan.md`, `docs/v1_scope_baseline.md` |
| Last updated | 2026-07-19 |

## 1. Document Purpose

This document defines the logical components of PlantGuard UAV v1.0 and assigns each component one clear area of ownership.

For every component, it specifies:

- purpose;
- responsibilities;
- non-responsibilities;
- owned data;
- inputs;
- outputs;
- direct dependencies;
- failure behavior;
- test boundary;
- future extension points.

The purpose of this catalog is to prevent ambiguous ownership before implementation begins.

This document does not define exact source-file names, class names, database tables, API routes, deployment processes, or message schemas. Those are defined in later architecture and repository-design documents.

## 2. Component Ownership Principles

### 2.1 One Primary Owner

Every important responsibility must have one primary owner.

Other components may contribute data or execute work, but ownership of the decision or artifact must remain unambiguous.

### 2.2 Planning, Approval, and Execution Are Separate

For flight routes:

```text
Farmer Dashboard
→ expresses route intent

Survey Planner / Revisit Planner
→ produces a candidate executable route

Safety Supervisor
→ approves, restricts, or rejects the route

PX4/MAVSDK Vehicle Adapter
→ executes the approved route
```

### 2.3 Evidence and Final Decisions Are Separate

```text
Model services
→ produce per-image evidence

Multi-Image Result Aggregator
→ produces the final site result
```

### 2.4 Workflow and Safety Are Separate

```text
Mission Orchestrator
→ decides which workflow stage should happen next

Safety Supervisor
→ decides whether the requested flight action is permitted
```

### 2.5 Meaning and Storage Are Separate

```text
Mission Data Manager
→ understands artifact relationships and traceability

Persistence Layer
→ stores structured records and artifact references
```

### 2.6 Presentation Is Not Authority

The Farmer Dashboard displays system state and accepts operator intent.

It does not own authoritative mission state, safety policy, route execution, or model decisions.

## 3. Component Inventory

1. Farmer Dashboard
2. Mission API
3. Mission Orchestrator
4. Safety Supervisor
5. PX4/MAVSDK Vehicle Adapter
6. Survey Planner
7. Camera Manager
8. Mission Data Manager
9. Image Quality Validator
10. Aerial Health Screening Service
11. Suspicious-Site Clusterer
12. Revisit Planner
13. Revisit Health Reassessment Service
14. PlantGuard Disease Classifier
15. Multi-Image Result Aggregator
16. Geospatial Mapper
17. Report Generator
18. Background Job Worker
19. Persistence Layer
20. Model Registry and Metadata Manager
21. Observability and Event Logger

## 4. Farmer Dashboard

### Purpose

Provide the farmer/operator-facing interface for mission setup, route intent, supervision, control, and result review.

### Responsibilities

- saved-field selection;
- mission setup;
- readiness and preflight display;
- operator takeoff approval;
- live mission status;
- warnings;
- pause, abort, and return-home requests;
- field map and evidence preview;
- final report display;
- route-intent editing;
- exclusion-zone editing;
- priority-zone editing;
- preferred survey-direction input;
- custom-route draft input where enabled;
- route preview;
- incomplete-coverage warnings.

### Route-Intent Modes

```text
automatic_coverage
guided_automatic
expert_custom
```

#### Automatic Coverage

The farmer selects a field and the system generates full-field coverage automatically.

#### Guided Automatic

The farmer may define:

- priority zones;
- exclusion zones;
- preferred survey direction;
- denser coverage areas;
- permitted altitude, overlap, or speed preferences within configured limits.

The Survey Planner converts these constraints into a candidate route.

#### Expert Custom

An authorized operator may draw a custom route draft.

The route draft is not directly executable. It must be normalized by the Survey Planner and validated by the Safety Supervisor.

### Required Coverage Warning

When the farmer excludes part of the field, the dashboard must clearly state:

```text
The excluded area will not be inspected.
Final field-health percentages will describe only the surveyed region.
```

### Non-Responsibilities

- executable waypoint generation;
- route-safety approval;
- direct MAVSDK or PX4 communication;
- mission-state transitions;
- AI inference;
- direct database writes;
- flight-controller failsafes.

### Owned Data

Only temporary presentation and unsaved-input state, such as:

- selected view;
- unsaved route draft;
- unsaved priority/exclusion edits;
- local display filters.

### Inputs

- field summaries;
- route previews;
- preflight results;
- mission status;
- telemetry summaries;
- warnings;
- map layers;
- evidence references;
- final results;
- reports.

### Outputs

- field-selection request;
- mission-creation request;
- route-intent request;
- takeoff approval;
- pause, abort, and return-home requests;
- retention/deletion requests.

### Direct Dependencies

- Mission API only.

### Failure Behavior

Dashboard failure must not remove PX4 safety, manual control, or healthy mission-service operation. After restart, it reconstructs its view from authoritative persisted state.

### Test Boundary

Use a mocked Mission API and simulate mission states, warnings, route-intent validation, custom-route rejection, and incomplete-coverage warnings.

### Future Extension Points

- mobile frontend;
- multilingual interface;
- historical analytics;
- offline tablet UI.

## 5. Mission API

### Purpose

Expose controlled application operations to the dashboard and approved clients.

### Responsibilities

- transport-level validation;
- request parsing;
- response formatting;
- authentication/authorization when implemented;
- translation of requests into application commands;
- command acknowledgment;
- status and result retrieval;
- correlation-ID propagation;
- explicit errors.

### Non-Responsibilities

- mission workflow;
- safety decisions;
- route generation;
- flight execution;
- model inference;
- database-driver logic.

### Owned Data

- request context;
- authenticated-user context;
- correlation IDs;
- transport errors.

### Inputs

- dashboard requests;
- identifiers;
- route-intent payloads;
- operator commands.

### Outputs

- application commands;
- status/result responses;
- acknowledgments;
- structured errors.

### Direct Dependencies

- Mission Orchestrator;
- application query services;
- Observability and Event Logger.

### Failure Behavior

No new dashboard command is accepted. Manual control and PX4-native safety remain available.

### Test Boundary

Use application-service mocks, invalid payloads, authorization failures, retries, and timeouts.

### Future Extension Points

- mobile API;
- local network authentication;
- engineering read-only API.

## 6. Mission Orchestrator

### Purpose

Coordinate the complete mission workflow.

### Responsibilities

- authoritative application mission state;
- legal state transitions;
- workflow progression;
- preflight coordination;
- waiting for operator approval;
- takeoff, survey, analysis, revisit, return, landing, and reporting coordination;
- asynchronous job initiation;
- component-event handling;
- final mission outcome.

### Non-Responsibilities

- PX4 low-level control;
- safety-rule definitions;
- route geometry;
- image/model algorithms;
- database implementation;
- dashboard rendering.

### Owned Data

- mission state;
- current phase;
- workflow checkpoint;
- active job and route references;
- final mission outcome.

### Inputs

- mission commands;
- operator commands;
- preflight results;
- vehicle/camera events;
- processing events;
- safety decisions.

### Outputs

- workflow commands;
- state-change events;
- job requests;
- route-planning requests;
- vehicle-action requests;
- report requests.

### Direct Dependencies

- Safety Supervisor;
- Vehicle Adapter;
- Survey Planner;
- Camera Manager;
- Background Job Worker;
- Mission Data Manager;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Stop new application decisions, preserve last state, permit PX4-native safety, and require a new recovery mission for physical continuation.

### Test Boundary

Use deterministic fakes, state-machine tests, failure injection, duplicate events, and invalid transition attempts.

### Future Extension Points

- companion coordination;
- post-flight-only workflows;
- additional mission profiles.

## 7. Safety Supervisor

### Purpose

Apply application-level safety policy.

### Responsibilities

- preflight;
- PASS/WARNING/BLOCKED results;
- battery feasibility;
- weather-mode validation;
- route and geofence validation;
- operator-approval validation;
- camera/model readiness policy;
- takeoff, survey, revisit, return, and recovery authorization;
- safety reason codes and records.

### Non-Responsibilities

- PX4-native failsafes;
- motor control;
- route generation;
- command execution;
- AI inference;
- mission progression.

### Owned Data

- preflight result;
- safety decision;
- route-validation result;
- battery/weather assessments;
- reason codes.

### Inputs

- routes;
- telemetry;
- battery;
- GPS/home;
- boundaries/exclusions;
- weather/hardware state;
- operator approval;
- model/camera readiness;
- mission state.

### Outputs

- approved;
- approved with restrictions;
- rejected;
- return required;
- emergency escalation.

### Direct Dependencies

- Vehicle Adapter;
- Persistence Layer;
- configuration;
- Observability and Event Logger.

### Failure Behavior

Block new application flight actions and preserve PX4-native safety.

### Test Boundary

Use simulated telemetry, routes, weather, battery, model/camera, and recovery scenarios.

### Future Extension Points

- hardware policy profiles;
- richer obstacle metadata;
- regulatory profiles.

## 8. PX4/MAVSDK Vehicle Adapter

### Purpose

Translate validated commands into MAVSDK/PX4 operations and convert PX4 state into application events.

### Responsibilities

- connection;
- telemetry subscription/normalization;
- takeoff;
- mission upload/start;
- hold;
- return-home;
- land;
- command acknowledgment;
- PX4 event translation;
- route progress;
- manual-takeover detection where available.

### Non-Responsibilities

- safety policy;
- mission workflow;
- route generation;
- battery policy;
- AI inference;
- dashboard interaction.

### Owned Data

- connection state;
- normalized telemetry;
- command acknowledgment;
- uploaded mission reference;
- last known mode.

### Inputs

- validated vehicle commands;
- approved routes;
- PX4 telemetry/results.

### Outputs

- acknowledgments;
- telemetry;
- vehicle and route events;
- link-loss/manual-takeover events.

### Direct Dependencies

- MAVSDK;
- PX4;
- Observability and Event Logger.

### Failure Behavior

Issue no new commands, preserve last state, and leave PX4-native safety/manual control active.

### Test Boundary

PX4 SITL, MAVSDK mocks, telemetry replay, command rejection, and link-loss tests.

### Future Extension Points

- alternate transport;
- companion proxy;
- compatible vehicle adapters.

## 9. Survey Planner

### Purpose

Convert field geometry and farmer route intent into a candidate executable survey route.

### Responsibilities

- field and exclusion processing;
- priority-zone processing;
- custom-route normalization;
- grid/lawnmower generation;
- waypoint and capture-point generation;
- route direction;
- overlap geometry;
- configured altitude/speed application;
- distance/duration estimation;
- coverage and skipped-area calculation;
- route-preview geometry.

### Route-Intent Inputs

```text
automatic coverage
priority zones
exclusion zones
preferred sweep direction
higher-density areas
custom route draft
permitted altitude/speed/overlap preferences
```

### Custom-Route Rule

A custom route draft is operator intent, not an executable command. The planner normalizes it, calculates expected coverage and skipped areas, and produces a candidate route for safety validation.

### Non-Responsibilities

- final safety approval;
- battery-policy authority;
- route execution;
- PX4 communication;
- capture;
- perception;
- dashboard rendering.

### Owned Data

- candidate survey plan;
- waypoints/capture points;
- coverage estimate;
- distance/duration;
- skipped-area geometry;
- planning metadata.

### Inputs

- field geometry;
- exclusions/priorities;
- route mode and intent;
- altitude/speed/overlap;
- home;
- camera geometry where available.

### Outputs

- candidate route;
- preview;
- coverage/skipped-area data;
- planning warnings;
- duration/distance estimates.

### Direct Dependencies

- geospatial utilities;
- configuration;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Create no executable route, preserve correction details, and keep mission before takeoff.

### Test Boundary

Polygons, holes, priority zones, malformed custom routes, coverage calculations, deterministic routes.

### Future Extension Points

- terrain awareness;
- crop-row routing;
- adaptive density;
- historical hotspot emphasis.

## 10. Camera Manager

### Purpose

Coordinate camera capture and mission association.

### Responsibilities

- connection and health;
- test capture;
- survey/revisit captures;
- retries;
- image IDs/timestamps;
- telemetry association;
- metadata;
- capture events;
- gimbal coordination where applicable.

### Non-Responsibilities

- image-quality judgment;
- classification;
- planning;
- mission state;
- clustering.

### Owned Data

- camera state;
- capture state;
- metadata;
- retry/failure data.

### Inputs

- capture command;
- route/capture context;
- telemetry;
- camera responses.

### Outputs

- ImageCaptured;
- ImageCaptureFailed;
- image reference;
- metadata.

### Direct Dependencies

- camera adapter;
- Mission Data Manager;
- Vehicle Adapter;
- Observability and Event Logger.

### Failure Behavior

Retry by policy, preserve failure evidence, and escalate repeated/global failure.

### Test Boundary

Mocked camera, delayed/failed capture, corrupt output, missing metadata, retries.

### Future Extension Points

- alternate cameras;
- onboard service;
- gimbal support;
- burst capture.

## 11. Mission Data Manager

### Purpose

Coordinate mission artifacts and traceability.

### Responsibilities

- artifact layout/naming;
- manifests;
- configuration/software/model snapshots;
- mission-image-observation-site-revisit-result links;
- artifact lifecycle;
- traceability validation.

### Non-Responsibilities

- storage-driver implementation;
- inference;
- safety;
- planning;
- UI.

### Owned Data

- artifact manifests;
- relationship metadata;
- snapshot references.

### Inputs

- mission entities;
- images;
- results;
- model/config metadata.

### Outputs

- artifact references;
- manifests;
- validated relationship records;
- lifecycle events.

### Direct Dependencies

- Persistence Layer;
- Model Registry;
- Observability and Event Logger.

### Failure Behavior

Stop new unauditable decisions, preserve raw evidence, and escalate.

### Test Boundary

Temporary storage, duplicates, missing references, interrupted writes, partial recovery.

### Future Extension Points

- archival export;
- retention automation;
- companion-buffer reconciliation.

## 12. Image Quality Validator

### Purpose

Determine whether an image is suitable for perception.

### Responsibilities

- readability/corruption;
- blur;
- exposure;
- obstruction;
- plant visibility;
- size;
- metadata completeness;
- quality score;
- accepted/rejected status and reason codes.

### Non-Responsibilities

- health/disease classification;
- camera retry execution;
- routing;
- final site result.

### Owned Data

- quality result;
- score;
- reasons;
- validator version.

### Inputs

- image reference;
- metadata;
- configuration.

### Outputs

- accepted/rejected image result;
- quality metrics/reasons.

### Direct Dependencies

- Mission Data Manager;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Never silently accept; preserve image; record failure; retry or mark incomplete.

### Test Boundary

Sharp/blurred, exposure, corrupt, missing metadata, and obstruction fixtures.

### Future Extension Points

- learned quality model;
- onboard validation;
- crop-aware thresholds.

## 13. Aerial Health Screening Service

### Purpose

Produce healthy, unhealthy, or uncertain survey observations.

### Responsibilities

- preprocessing;
- inference;
- output/confidence validation;
- label mapping;
- decision policy;
- observation creation;
- model/preprocessing version recording;
- unsupported-input handling.

### Non-Responsibilities

- clustering;
- revisit planning;
- disease classification;
- final site result;
- flight commands;
- mission progression.

### Owned Data

- screening results;
- observations;
- confidence/model references;
- failure reason.

### Inputs

- accepted survey image;
- metadata;
- active model contract;
- confidence policy.

### Outputs

- healthy/unhealthy/uncertain observations;
- metrics/events.

### Direct Dependencies

- Image Quality Validator;
- Model Registry;
- Mission Data Manager;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Preserve images/completed observations, disable automatic AI revisit generation, and allow later resume.

### Test Boundary

Fixed images, invalid outputs, unsupported crops, threshold boundaries.

### Future Extension Points

- TensorRT;
- native C++;
- onboard screening;
- ensembles.

## 14. Suspicious-Site Clusterer

### Purpose

Group related unhealthy and uncertain observations into physical sites.

### Responsibilities

- observation selection;
- geographic clustering;
- duplicate suppression;
- site creation/update;
- representative location;
- supporting membership;
- clustering provenance;
- priority evidence.

### Non-Responsibilities

- route generation;
- safety;
- disease prediction;
- capture;
- final route ordering;
- final result.

### Owned Data

- suspicious site;
- observation membership;
- representative coordinates;
- clustering metadata.

### Inputs

- unhealthy/uncertain observations;
- geographic metadata;
- configuration.

### Outputs

- created/updated sites;
- deduplicated site set;
- metrics.

### Direct Dependencies

- geospatial utilities;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Preserve observations, create no untraceable sites, and allow retry.

### Test Boundary

Known clusters, duplicates, outliers, field-edge cases.

### Future Extension Points

- crop-row clustering;
- cross-mission clustering;
- learned association.

## 15. Revisit Planner

### Purpose

Generate a candidate revisit route.

### Responsibilities

- candidate-site selection;
- priority ordering;
- route ordering;
- revisit waypoints/capture points;
- distance/duration estimates;
- safe-subset candidate generation;
- planning skip reasons.

### Non-Responsibilities

- final safety approval;
- battery-policy authority;
- execution;
- classification;
- final result;
- PX4 communication.

### Owned Data

- candidate revisit route;
- ordered targets;
- estimates;
- planning metadata.

### Inputs

- suspicious sites;
- boundaries/exclusions;
- home;
- revisit configuration;
- priority policy;
- approximate time/energy budget.

### Outputs

- candidate route;
- ordered targets;
- estimates;
- skipped candidate reasons.

### Direct Dependencies

- geospatial utilities;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Preserve sites, emit explicit failure, and create no executable route.

### Test Boundary

Zero/one/many sites, unreachable sites, priorities, distance constraints.

### Future Extension Points

- vehicle-routing optimization;
- historical severity weighting;
- onboard planning.

## 16. Revisit Health Reassessment Service

### Purpose

Produce per-image healthy, unhealthy, or uncertain results from revisit imagery.

### Responsibilities

- revisit preprocessing;
- health inference;
- output validation;
- confidence;
- model-version recording;
- unsupported handling.

### Non-Responsibilities

- disease classification;
- multi-image aggregation;
- route planning;
- quality validation;
- final persistence.

### Owned Data

- per-image health result;
- confidence;
- model reference;
- failure reason.

### Inputs

- accepted revisit image;
- metadata;
- active model;
- confidence policy.

### Outputs

- per-image health result;
- processing event.

### Direct Dependencies

- Image Quality Validator;
- Model Registry;
- Mission Data Manager;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Preserve imagery, force no status, permit retry, and propagate unresolved handling.

### Test Boundary

Deterministic images, threshold boundaries, invalid output, unsupported crop.

### Future Extension Points

- shared backbone;
- TensorRT/C++;
- onboard inference.

## 17. PlantGuard Disease Classifier

### Purpose

Produce per-image disease evidence from unhealthy revisit imagery.

### Responsibilities

- preprocessing;
- inference;
- output/class-order validation;
- top-k predictions;
- confidence;
- supported-class checks;
- model-version recording.

### Non-Responsibilities

- health decision;
- final disease result;
- multi-image combination;
- manual-inspection policy;
- mission state;
- routing.

### Owned Data

- per-image disease evidence;
- top-k scores;
- model references;
- failure reason.

### Inputs

- accepted revisit image;
- unhealthy health result;
- active model contract;
- confidence configuration.

### Outputs

- disease evidence;
- top-k/confidence;
- unsupported/failed result.

### Direct Dependencies

- Revisit Health Reassessment Service;
- Model Registry;
- Mission Data Manager;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Preserve imagery and health result, force no label, permit later classification.

### Test Boundary

Supported/unsupported classes, invalid shapes, class-order mismatch, confidence boundaries.

### Future Extension Points

- TensorRT;
- native C++;
- companion deployment;
- ensembles.

## 18. Multi-Image Result Aggregator

### Purpose

Combine per-image revisit evidence into one final site result.

### Responsibilities

- select valid evidence;
- quality-aware weighting;
- health/disease agreement;
- threshold application;
- disease withholding;
- final status/confidence;
- manual-inspection recommendation;
- reason codes.

### Non-Responsibilities

- inference;
- capture;
- routing;
- safety;
- UI;
- database mechanics.

### Owned Data

- aggregate evidence;
- agreement metrics;
- final site result;
- final reasons.

### Inputs

- quality results;
- per-image health results;
- per-image disease evidence;
- model metadata;
- aggregation policy.

### Outputs

- healthy_after_suspicious_survey;
- unhealthy_disease_identified;
- unhealthy_disease_uncertain;
- health_status_unresolved;
- manual_inspection_recommended.

### Direct Dependencies

- Revisit Health Reassessment Service;
- Disease Classifier;
- Model Registry;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Preserve all evidence, force no result, permit retry, and recommend inspection where required.

### Test Boundary

Unanimous/conflicting evidence, mixed quality, missing classifier output, threshold cases.

### Future Extension Points

- Bayesian fusion;
- learned multi-view fusion;
- temporal evidence.

## 19. Geospatial Mapper

### Purpose

Create geographic mission representations and coverage products.

### Responsibilities

- observation/site geolocation representation;
- field/route/flight-path GeoJSON;
- observation/site/revisit/final-result GeoJSON;
- usable coverage;
- skipped-area geometry;
- map layers;
- geospatial error metadata.

### Non-Responsibilities

- clustering policy;
- route execution;
- inference;
- safety;
- report wording.

### Owned Data

- geographic features;
- coverage layers;
- map artifacts;
- geospatial metadata.

### Inputs

- field geometry;
- routes;
- telemetry;
- observations;
- sites;
- final results.

### Outputs

- GeoJSON;
- coverage metrics;
- map layers;
- location-error metrics.

### Direct Dependencies

- Mission Data Manager;
- Persistence Layer;
- Observability and Event Logger.

### Failure Behavior

Preserve structured results, mark mapping failed, and allow regeneration.

### Test Boundary

Known coordinates, polygons, coverage fixtures, missing-location cases.

### Future Extension Points

- historical overlays;
- mobile maps;
- higher-precision positioning.

## 20. Report Generator

### Purpose

Produce farmer-facing and engineering-facing reports from persisted authoritative results.

### Responsibilities

- mission summary;
- field-health and disease summaries;
- unresolved/warning/failure summaries;
- coverage summary;
- evidence links;
- HTML and machine-readable report;
- report status.

### Non-Responsibilities

- inference;
- result modification;
- routing;
- safety;
- flight commands;
- independent reinterpretation.

### Owned Data

- report artifacts;
- report metadata;
- generation status.

### Inputs

- mission state;
- final results;
- maps;
- evidence;
- warnings/failures;
- metrics.

### Outputs

- farmer report;
- engineering summary;
- ReportGenerated event.

### Direct Dependencies

- Persistence Layer;
- Mission Data Manager;
- Geospatial Mapper;
- Observability and Event Logger.

### Failure Behavior

Preserve all underlying results, permit retry, and expose raw results where possible.

### Test Boundary

Complete, partial, warning-heavy, no-site, and unresolved-site missions.

### Future Extension Points

- PDF export;
- printable summaries;
- historical analytics.

## 21. Background Job Worker

### Purpose

Execute long-running work outside immediate API requests.

### Responsibilities

- job execution/status/progress;
- retries;
- checkpoints/resume;
- failure recording;
- safe cancellation;
- worker health;
- resource reporting.

### Typical Jobs

```text
image validation
screening
clustering
revisit analysis
disease classification
aggregation
mapping
reporting
reprocessing
benchmarking
```

### Non-Responsibilities

- workflow policy;
- mission-state authority;
- safety;
- model semantics;
- final decisions.

### Owned Data

- job record;
- progress;
- retries;
- checkpoint;
- failure details;
- worker health.

### Inputs

- job request;
- artifact references;
- component operation;
- retry policy.

### Outputs

- progress/completion/failure events;
- checkpoints.

### Direct Dependencies

- processing services;
- Persistence Layer;
- Mission Data Manager;
- Observability and Event Logger.

### Failure Behavior

Preserve checkpoints, record exact failure, retry only by policy, and avoid duplicate side effects.

### Test Boundary

Injected crash, retry, duplicate delivery, checkpoint resume.

### Future Extension Points

- distributed local workers;
- companion worker;
- GPU scheduling;
- native C++ worker.

## 22. Persistence Layer

### Purpose

Store authoritative structured state and artifact references.

### Responsibilities

- all field, mission, state, image, observation, site, revisit, result, job, safety, and event records;
- transactions;
- repositories;
- schema migrations.

### Non-Responsibilities

- product decisions;
- routing;
- inference;
- report interpretation;
- API semantics;
- workflow.

### Owned Data

- all authoritative structured records.

### Inputs

- validated entities;
- queries;
- transaction requests.

### Outputs

- persisted/query/transaction results;
- storage errors.

### Direct Dependencies

- selected relational database;
- artifact-reference mechanism;
- Observability and Event Logger.

### Failure Behavior

Never silently discard state; stop new unauditable decisions; use local buffering only where safe; escalate.

### Test Boundary

In-memory/test database, rollback, duplicates, interrupted writes, migrations.

### Future Extension Points

- PostgreSQL;
- alternate local database;
- archival export.

## 23. Model Registry and Metadata Manager

### Purpose

Control active model artifacts and contracts.

### Responsibilities

- IDs/versions/locations/hashes;
- input/output contracts;
- preprocessing;
- class ordering;
- supported crops/classes;
- confidence policies;
- active-model selection;
- compatibility validation.

### Non-Responsibilities

- inference;
- training;
- final decisions;
- mission state.

### Owned Data

- model metadata;
- active assignments;
- preprocessing/class/confidence contracts.

### Inputs

- model registration;
- artifact/metadata;
- compatibility query.

### Outputs

- validated contract;
- active model;
- compatibility error;
- metadata snapshot.

### Direct Dependencies

- Persistence Layer;
- Mission Data Manager;
- Observability and Event Logger.

### Failure Behavior

Block model use and normal preflight when required metadata is missing/incompatible.

### Test Boundary

Valid/invalid metadata, hash mismatch, class-order mismatch, unsupported crop, shape mismatch.

### Future Extension Points

- TensorRT engines;
- native C++ metadata;
- performance history.

## 24. Observability and Event Logger

### Purpose

Record what the system did and why.

### Responsibilities

- mission/command/state/warning/failure/job events;
- component health;
- latency/resource metrics;
- correlation IDs;
- append-only audit history.

### Non-Responsibilities

- decisions;
- response policy;
- routing;
- inference;
- transaction policy.

### Owned Data

- event stream;
- logs;
- metrics;
- correlation metadata.

### Inputs

- all component events/metrics/warnings/failures.

### Outputs

- structured logs;
- metrics;
- audit records;
- diagnostics.

### Direct Dependencies

- local log storage;
- Persistence Layer for structured audit records.

### Failure Behavior

Attempt local fallback; never falsely claim decisions were audited; escalate persistent audit loss.

### Test Boundary

Known event chains, log failure, duplicate events, metric aggregation.

### Future Extension Points

- local dashboards;
- tracing;
- companion log reconciliation;
- benchmark export.

## 25. Primary Ownership Matrix

| Responsibility | Primary owner |
|---|---|
| Farmer interaction | Farmer Dashboard |
| Farmer route intent | Farmer Dashboard |
| Executable survey route | Survey Planner |
| Executable revisit route | Revisit Planner |
| Route safety approval | Safety Supervisor |
| Route execution | Vehicle Adapter |
| API transport validation | Mission API |
| Mission workflow | Mission Orchestrator |
| Application safety | Safety Supervisor |
| PX4 communication | Vehicle Adapter |
| Camera operation | Camera Manager |
| Artifact traceability | Mission Data Manager |
| Image usability | Image Quality Validator |
| Survey screening | Aerial Health Screening Service |
| Observation grouping | Suspicious-Site Clusterer |
| Revisit health evidence | Revisit Health Reassessment Service |
| Disease evidence | PlantGuard Disease Classifier |
| Final site result | Multi-Image Result Aggregator |
| Geospatial outputs | Geospatial Mapper |
| Mission report | Report Generator |
| Long-running execution | Background Job Worker |
| Structured storage | Persistence Layer |
| Model contracts | Model Registry and Metadata Manager |
| Logs and metrics | Observability and Event Logger |

## 26. Critical Separation Rules

```text
Dashboard → route intent
Planner → candidate route
Safety Supervisor → route approval
Vehicle Adapter → route execution
```

```text
Mission Orchestrator → requests next stage
Safety Supervisor → permits or rejects it
```

```text
Model services → per-image evidence
Result Aggregator → final site result
```

```text
Mission Data Manager → artifact meaning and traceability
Persistence Layer → storage mechanics
```

## 27. Failure Ownership Examples

### Camera Disconnect

```text
Camera Manager detects
→ Logger records
→ Orchestrator coordinates
→ Safety Supervisor decides safe response
→ Vehicle Adapter executes approved return
```

### Screening Worker Crash

```text
Worker detects
→ Screening Service reports incomplete processing
→ Orchestrator disables automatic revisit
→ Safety Supervisor evaluates remaining safe behavior
```

### Invalid Custom Route

```text
Dashboard submits intent
→ Survey Planner normalizes/rejects geometry
→ Safety Supervisor rejects unsafe candidate
→ Dashboard displays correction
```

### Disease Disagreement

```text
Classifier produces per-image predictions
→ Aggregator detects insufficient agreement
→ final result is unhealthy_disease_uncertain
```

## 28. Day 2 Frozen Decisions

1. Mission Orchestrator owns workflow progression.
2. Safety Supervisor owns application safety decisions.
3. Vehicle Adapter owns command translation and execution.
4. Farmer Dashboard owns route-intent editing and preview.
5. Survey Planner owns candidate survey-route generation.
6. Revisit Planner owns candidate revisit-route generation.
7. A farmer-drawn route is a route request, not a direct PX4 command.
8. Exclusion and priority zones are supported.
9. Dashboard warns when exclusions reduce inspected coverage.
10. Planners propose but do not approve or execute.
11. Camera Manager owns capture, not interpretation.
12. Image Quality Validator owns image acceptance.
13. Screening Service owns survey observations.
14. Site Clusterer owns grouping and deduplication.
15. Revisit Reassessment owns per-image revisit health evidence.
16. Disease Classifier owns per-image disease evidence.
17. Result Aggregator owns final site outcomes.
18. Geospatial Mapper owns geographic representations.
19. Report Generator presents persisted truth.
20. Mission Data Manager owns traceability.
21. Persistence Layer owns storage mechanics.
22. Model Registry owns model contracts.
23. Worker executes long-running work, not workflow policy.
24. Observability records but does not decide.
25. Only Vehicle Adapter communicates directly with PX4.
26. No AI component issues flight commands.
27. No UI component owns authoritative mission state.

## 29. Day 2 Acceptance Criteria

Day 2 is complete when:

- every required component is defined;
- each has one primary purpose;
- responsibilities and non-responsibilities are explicit;
- data, inputs, outputs, dependencies, failures, tests, and extensions are defined;
- farmer route intent is supported without bypassing planning or safety;
- no two components ambiguously own the same responsibility;
- the catalog is ready for Day 3 interface design.

## 30. Final Component Statement

PlantGuard UAV separates:

```text
farmer intent
route generation
safety approval
vehicle execution
image capture
image validation
model evidence
final result aggregation
geospatial presentation
persistence
observability
```

This allows flexible farmer input without sacrificing safety, traceability, testability, or replaceable implementation boundaries.
