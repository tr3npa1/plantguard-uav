# PlantGuard UAV — System Architecture

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | System Architecture |
| Target release | v1.0 |
| Status | Active architecture baseline |
| Related documents | `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md`, `docs/verification_and_acceptance_plan.md`, `docs/v1_scope_baseline.md` |
| Last updated | 2026-07-19 |

## 1. Document Purpose

This document defines the top-level logical architecture of PlantGuard UAV v1.0.

It establishes:

- the PlantGuard UAV system boundary;
- external actors, hardware, and software systems;
- the ground-station-first deployment model;
- the optional companion-computer extension boundary;
- the architectural layers;
- allowed dependency direction;
- the separation of flight safety, mission policy, perception, persistence, and user interface concerns;
- control-plane and data-plane behavior;
- synchronous and asynchronous interaction patterns;
- source-of-truth ownership;
- trust boundaries;
- failure boundaries;
- quality attributes;
- intentionally deferred architecture values.

This document does not define individual source files, classes, database tables, API endpoints, or concrete process boundaries. Those details are defined in later Week 2 architecture documents and Week 3 repository design.

## 2. Architectural Scope

PlantGuard UAV v1.0 is a local-first, operator-authorized, autonomous RGB field-inspection system for one predefined agricultural field and one drone at a time.

The architecture supports the following product flow:

```text
select saved field
→ run preflight
→ obtain operator approval
→ take off
→ survey the complete field
→ capture geotagged RGB imagery
→ validate image quality
→ screen observations as healthy / unhealthy / uncertain
→ group suspicious observations into sites
→ generate a safe revisit mission
→ revisit eligible suspicious sites
→ capture higher-detail imagery
→ reassess health
→ classify disease where evidence is sufficient
→ preserve uncertainty where evidence is insufficient
→ return home
→ land
→ generate field map and report
```

The architecture shall not introduce:

- direct wide-area disease diagnosis as a replacement for revisit classification;
- treatment recommendations;
- spraying;
- autonomous takeoff without operator authorization;
- cloud dependency;
- automatic physical-flight resume after interruption;
- direct dashboard-to-flight-controller commands.

## 3. Architecture Principles

The following principles are authoritative.

### 3.1 Safety Before Mission Completion

No field-coverage, revisit, model, latency, or reporting objective may override safe flight or recovery.

### 3.2 Native Flight Safety Remains Authoritative

PX4 and the selected flight controller own:

- stabilization;
- motor control;
- attitude control;
- position control;
- native geofence;
- native battery failsafes;
- native loss-of-link behavior;
- return-to-home execution;
- landing execution;
- manual-controller priority.

PlantGuard shall not replace or disable these mechanisms.

### 3.3 Application Safety Is Separate From Native Safety

PlantGuard owns application-level safety policy, including:

- preflight validation;
- route validation;
- battery-feasibility checks;
- weather-mode checks;
- revisit feasibility;
- abort policy;
- return-home policy;
- recovery-mission rules.

Application safety may restrict or reject commands, but it does not perform low-level flight control.

### 3.4 Manual Control Is Independent

The operator's physical manual-control path must remain available even when:

- the dashboard fails;
- the Mission API fails;
- the Mission Orchestrator fails;
- a model worker crashes;
- local storage becomes unavailable.

### 3.5 Local-First and Offline-Capable

Core v1.0 operation shall not depend on:

- cloud services;
- cloud synchronization;
- external inference APIs;
- remote databases;
- persistent internet connectivity.

### 3.6 Ground-Station-First

The core v1.0 architecture runs mission orchestration, perception, persistence, mapping, reporting, and the farmer interface on the ground station.

### 3.7 Stable Interfaces Before Optimization

Mission logic shall depend on abstract interfaces rather than directly on:

- MAVSDK;
- PX4 protocol details;
- ONNX Runtime;
- TensorRT;
- SQLite;
- PostgreSQL;
- a specific job queue;
- a specific camera SDK.

### 3.8 Evidence Is Not State Ownership

AI models produce evidence and predictions.

They do not own:

- mission state;
- operator authorization;
- flight commands;
- safety decisions;
- final persistence policy.

### 3.9 Partial Work Must Survive Failure

Long-running processing shall be checkpointed.

Valid completed work shall not be discarded because a later stage fails.

### 3.10 Physical Flight Does Not Auto-Resume

Data processing may resume from saved checkpoints.

Physical flight requires a new recovery mission, new preflight, and new operator approval.

## 4. System Boundary

### 4.1 Inside PlantGuard UAV

The PlantGuard UAV software boundary includes the following logical capabilities:

```text
Farmer Dashboard
Mission API
Mission Orchestration
Application-Level Safety Supervision
Survey Planning
Revisit Planning
Vehicle Integration
Camera Coordination
Mission Data Management
Image Quality Validation
Aerial Health Screening
Suspicious-Site Grouping
Revisit Health Reassessment
Disease Classification
Multi-Image Aggregation
Geospatial Mapping
Report Generation
Persistence
Background Processing
Configuration Management
Model Metadata Management
Observability
Event Logging
Checkpointing
```

These are logical responsibilities. They are not yet fixed to one source file or one process.

### 4.2 Outside PlantGuard UAV

The following remain external:

```text
Farmer/operator
Drone airframe
Motors and propulsion
PX4 flight controller
Manual radio controller
RGB camera hardware
GPS and flight sensors
Ground-station computer hardware
Optional companion-computer hardware
Operating system
Physical field
Weather
Applicable aviation regulation
Manufacturer limitations
```

PlantGuard communicates with these entities but does not own their internal implementation.

### 4.3 External Responsibility Boundary

Examples:

```text
PlantGuard requests takeoff
→ PX4 validates and executes the low-level flight action

PlantGuard requests return-to-home
→ PX4 executes the configured return behavior

PlantGuard records camera metadata
→ the camera hardware produces the image

PlantGuard validates mission legality in configuration
→ the operator remains responsible for actual regulatory compliance
```

## 5. External Actors

### 5.1 Farmer

The farmer:

- selects a saved field;
- views readiness;
- approves takeoff;
- views mission progress;
- views field-health results;
- reviews evidence;
- receives manual-inspection recommendations;
- may delete retained mission imagery.

The farmer does not directly operate internal model or storage configuration.

### 5.2 Operator

The operator may be the farmer or another authorized person.

The operator:

- supervises the flight;
- confirms the takeoff area is safe;
- confirms weather suitability;
- approves takeoff;
- may pause;
- may abort;
- may command return-home;
- may take manual control.

### 5.3 PX4 Flight Controller

PX4:

- owns low-level flight safety;
- executes waypoints;
- executes return-home;
- performs landing;
- enforces native failsafes;
- reports telemetry;
- prioritizes manual control.

### 5.4 RGB Camera

The camera:

- produces survey and revisit imagery;
- provides capture metadata where available;
- may be physically attached to the drone or companion system.

### 5.5 Manual Controller

The manual controller provides an independent operator control path to the flight controller.

It shall not depend on the dashboard.

### 5.6 Ground Station

The ground station is the primary v1.0 application platform.

It hosts:

- farmer interface;
- mission logic;
- safety policy;
- route planning;
- perception;
- persistence;
- mapping;
- reporting;
- observability.

### 5.7 Optional Companion Computer

The companion computer is a planned extension.

It may later host selected hardware-adjacent and inference capabilities without changing the core mission contracts.

## 6. Top-Level System Context

```text
                    ┌──────────────────────┐
                    │   Farmer / Operator  │
                    └──────────┬───────────┘
                               │
               Select, approve, pause, abort,
                 return home, inspect results
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     PlantGuard UAV                           │
│                                                              │
│  Farmer Dashboard                                            │
│          │                                                   │
│          ▼                                                   │
│  Mission API                                                 │
│          │                                                   │
│          ▼                                                   │
│  Mission Orchestrator                                        │
│      ┌───────────────┬────────────────┬──────────────────┐    │
│      ▼               ▼                ▼                  ▼    │
│ Safety/Autonomy   Perception      Geospatial/Report  Persistence│
│      │               │                │                  │    │
│      └───────────────┴───────────────┬┴──────────────────┘    │
│                                      ▼                        │
│                       Hardware and Runtime Adapters            │
└───────────────────────────────┬───────────────────────────────┘
                                │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
        PX4 / Drone        RGB Camera       Local Storage
             ▲
             │
      Manual Controller
```

The manual controller has an independent path to the vehicle.

## 7. Core v1.0 Runtime Topology

### 7.1 Drone and Flight Controller

The drone side owns:

```text
stabilization
motor control
attitude control
position control
waypoint execution
native geofence
native battery failsafes
native telemetry-loss failsafes
return-to-home execution
landing execution
manual-controller priority
```

### 7.2 Ground Station

The ground station owns:

```text
farmer dashboard
mission configuration
application preflight
mission orchestration
survey planning
revisit planning
camera coordination
image ingestion
image quality
health screening
suspicious-site grouping
disease classification
geospatial mapping
report generation
structured persistence
artifact storage
logs and metrics
```

### 7.3 Communication Boundary

The ground station communicates with the vehicle through a hardware adapter, initially expected to use MAVSDK with PX4.

The architecture must tolerate communication interruption by relying on PX4-native behavior for immediate flight safety.

### 7.4 Why Ground-Station-First

The ground-station-first topology:

- avoids early companion-hardware dependency;
- provides more compute and storage;
- simplifies model iteration;
- improves observability;
- simplifies debugging;
- supports simulation and recorded-mission testing;
- keeps hardware optimization separate from product workflow.

## 8. Optional Companion-Computer Extension

The optional companion computer may later perform:

```text
camera coordination
image buffering
basic image-quality checks
lightweight health screening
mission-event buffering
hardware monitoring
offline fallback
ONNX Runtime inference
TensorRT inference
native C++ inference
```

It shall not replace:

```text
PX4 stabilization
PX4 native failsafes
manual controller
operator takeoff approval
application safety policy
persistent mission audit
```

### 8.1 Companion Deployment Rule

The same logical interfaces must remain valid whether inference runs:

```text
on the ground station
on the companion computer
through Python
through native C++
through ONNX Runtime
through TensorRT
```

Mission logic shall not be rewritten merely because the execution location changes.

### 8.2 Companion Synchronization Boundary

Companion-to-ground synchronization shall remain local.

Cloud synchronization is excluded.

The architecture must define later:

- which node is authoritative during temporary disconnection;
- how buffered events are replayed;
- how duplicate events are prevented;
- how mission state conflicts are rejected.

These are deferred to the runtime architecture document.

## 9. Architectural Layers

### 9.1 Farmer Interface Layer

#### Purpose

Present mission state and accept operator intent.

#### Responsibilities

- field selection;
- readiness display;
- operator approval;
- mission progress;
- warnings;
- pause;
- abort;
- return-home;
- field map;
- report;
- evidence preview.

#### Non-Responsibilities

- direct vehicle control;
- safety-policy ownership;
- model inference;
- direct database writes;
- raw route validation.

### 9.2 Application and Mission Layer

#### Purpose

Coordinate the complete inspection workflow.

#### Responsibilities

- mission creation;
- mission-state transitions;
- workflow coordination;
- command handling;
- event handling;
- background-job initiation;
- completion policy;
- failure-state policy.

#### Non-Responsibilities

- low-level flight control;
- raw tensor processing;
- storage-driver implementation;
- direct bypass of safety checks.

### 9.3 Safety and Autonomy Layer

#### Purpose

Validate whether requested mission actions are permitted and produce safe application-level routes.

#### Responsibilities

- preflight;
- battery feasibility;
- route validity;
- geofence checks;
- weather-mode validation;
- survey planning;
- revisit planning;
- application-level abort and return policy;
- recovery-mission rules.

#### Non-Responsibilities

- motor control;
- attitude stabilization;
- PX4-native failsafe implementation;
- disease classification.

### 9.4 Hardware Integration Layer

#### Purpose

Translate PlantGuard intent into hardware-facing operations and translate hardware state into application events.

#### Responsibilities

- MAVSDK/PX4 integration;
- camera integration;
- telemetry ingestion;
- capture commands;
- gimbal integration where applicable;
- companion-hardware integration;
- storage-device integration.

#### Non-Responsibilities

- mission policy;
- safety-policy ownership;
- model decisions;
- farmer report generation.

### 9.5 Perception Layer

#### Purpose

Transform accepted imagery into health and disease evidence.

#### Responsibilities

- image-quality validation;
- tiling;
- health screening;
- revisit health reassessment;
- disease classification;
- uncertainty handling;
- multi-image aggregation;
- model-output validation.

#### Non-Responsibilities

- flight commands;
- operator authorization;
- battery policy;
- route validation;
- mission-state ownership.

### 9.6 Geospatial and Reporting Layer

#### Purpose

Transform evidence into spatially organized field results.

#### Responsibilities

- observation geolocation;
- suspicious-site clustering;
- site deduplication;
- GeoJSON generation;
- map generation;
- mission metrics;
- farmer report;
- engineering report artifacts.

#### Non-Responsibilities

- low-level flight control;
- model-runtime implementation;
- preflight authorization.

### 9.7 Infrastructure Layer

#### Purpose

Provide persistence, asynchronous execution, configuration, health monitoring, and observability.

#### Responsibilities

- relational persistence;
- artifact storage;
- background workers;
- job queue;
- checkpointing;
- configuration;
- model metadata;
- logs;
- metrics;
- health checks.

#### Non-Responsibilities

- product decision logic;
- flight-policy decisions;
- health/disease interpretation.

## 10. Dependency Direction

The canonical dependency direction is:

```text
Farmer Dashboard
    ↓
Mission API
    ↓
Application / Mission Logic
    ↓
Domain Policies and Services
    ↓
Abstract Interfaces
    ↓
Vehicle, Camera, Model, Storage, and Database Adapters
```

### 10.1 Dependency Rule

Core mission and decision logic shall depend on interfaces, not concrete libraries.

Examples:

```text
Mission Orchestrator
→ depends on VehicleControl

MAVSDK Vehicle Adapter
→ implements VehicleControl
```

```text
Health Screening Service
→ depends on HealthScreeningModel

ONNX Runtime Adapter
→ implements HealthScreeningModel
```

```text
Mission Data Manager
→ depends on MissionRepository

SQLite or PostgreSQL Repository
→ implements MissionRepository
```

### 10.2 Forbidden Dependency Direction

The following are forbidden:

```text
Dashboard → MAVSDK directly
Model Runtime → mission-state mutation directly
Database Adapter → product-policy decisions
Camera Adapter → revisit-policy decisions
Report Generator → flight commands
```

## 11. Control Plane

The control plane contains commands, operational state, and safety decisions.

Examples:

```text
CreateMission
RunPreflight
ApproveTakeoff
StartSurvey
PauseMission
AbortMission
ReturnHome
StartRevisit
MissionStateChanged
BatteryWarning
VehicleHealthChanged
```

Control-plane messages are:

- relatively small;
- auditable;
- mission-correlated;
- strongly validated;
- subject to safety policy;
- often time-sensitive.

## 12. Data Plane

The data plane contains mission evidence and processing artifacts.

Examples:

```text
RGB images
image tiles
telemetry history
screening predictions
revisit predictions
GeoJSON
maps
reports
model outputs
logs
metrics
configuration snapshots
```

Data-plane operations are often:

- larger;
- asynchronous;
- checkpointed;
- retryable;
- stored as artifacts;
- referenced rather than embedded in status messages.

The dashboard should receive metadata and artifact references rather than full-resolution images in every mission update.

## 13. Synchronous Interactions

Synchronous request/response is appropriate for:

```text
select field
create mission
request preflight
approve takeoff
pause mission
abort mission
request return-home
read current status
```

An accepted command is not the same as completed physical action.

Example:

```text
ReturnHomeAccepted
```

does not mean:

```text
VehicleLanded
```

Physical completion is reported later through telemetry and mission events.

## 14. Asynchronous Processing

Asynchronous jobs or events are appropriate for:

```text
image ingestion
image validation
tiling
health screening
site clustering
revisit planning
multi-image aggregation
disease classification
map generation
report generation
reprocessing
benchmarking
```

Each asynchronous job shall support:

```text
job identifier
mission identifier
correlation identifier
status
progress
retry policy
checkpoint
failure reason
resume behavior
```

## 15. Nominal Control Flow

```text
Farmer selects field
→ Dashboard requests mission creation
→ Mission API validates request
→ Mission Orchestrator creates mission
→ Safety Supervisor runs preflight
→ Dashboard displays readiness
→ Farmer approves takeoff
→ Mission Orchestrator requests takeoff
→ Safety Supervisor validates action
→ Vehicle Adapter sends command
→ PX4 executes takeoff
→ Mission Orchestrator starts survey
→ Survey Planner supplies route
→ Safety Supervisor validates route
→ Vehicle Adapter uploads/executes route
→ Camera Manager coordinates capture
→ Mission Orchestrator observes survey completion
→ Safety Supervisor evaluates revisit feasibility
→ Revisit Planner creates revisit route
→ Safety Supervisor validates revisit route
→ Vehicle Adapter executes revisit route
→ Mission Orchestrator requests return-home
→ PX4 returns and lands
→ Report generation completes
```

Every flight action is subordinate to:

```text
operator commands
application safety policy
PX4 native safety behavior
```

## 16. Nominal Data Flow

```text
Camera captures survey image
→ raw image and metadata stored
→ Image Quality Validator accepts or rejects
→ accepted image enters Aerial Health Screening
→ screening produces observations
→ observations receive geographic context
→ unhealthy and uncertain observations enter clustering
→ cluster becomes suspicious site
→ suspicious site becomes revisit candidate
→ revisit images are captured
→ revisit images pass quality validation
→ health is reassessed
→ unhealthy evidence enters disease classifier
→ multi-image evidence is aggregated
→ final site result is persisted
→ Geospatial Mapper updates field map
→ Report Generator produces final report
```

Traceability shall be preserved throughout.

## 17. Source-of-Truth Ownership

| Information | Source of truth |
|---|---|
| Low-level vehicle state | PX4 telemetry |
| Physical manual input | Manual controller / flight controller |
| Application mission state | Mission Orchestrator and persistent mission record |
| Application safety decision | Safety Supervisor decision record |
| Raw image evidence | Mission artifact storage |
| Structured mission entities | Persistence Layer |
| Model identity and preprocessing | Model Registry and Metadata Manager |
| Final farmer-visible site result | Persisted Final Site Result |
| Audit history | Append-only mission event log |
| User interface state | Derived from current persisted and live mission state |

### 17.1 Dashboard Rule

The dashboard is a view and command-entry surface.

It is not the source of truth.

### 17.2 Model Rule

A model output is evidence.

It does not become a final product result until validated, contextualized, aggregated where required, and persisted.

## 18. Trust Boundaries

### 18.1 Operator Boundary

Only authorized local users should be able to:

```text
approve takeoff
abort
request return-home
modify fields
delete mission evidence
change safety-critical configuration
```

### 18.2 Vehicle Command Boundary

Only the validated vehicle-control path may issue application commands to the vehicle.

The dashboard shall never call MAVSDK directly.

### 18.3 Model Boundary

Model artifacts and metadata must be validated before use.

Inference completion alone does not make an output trustworthy.

### 18.4 Storage Boundary

Mission artifacts and records must not be mixed across missions.

Every artifact shall include or derive from mission identity.

### 18.5 Configuration Boundary

Safety-critical configuration changes must be versioned and recorded.

## 19. Failure Boundaries

### 19.1 Dashboard Failure

Dashboard failure must not stop:

```text
PX4 native safety
manual control
native return-to-home
healthy mission-service execution
```

### 19.2 Mission API Failure

Mission API failure must not remove:

```text
manual control
native failsafes
already active safe PX4 behavior
```

No new dashboard command is accepted until the API recovers.

### 19.3 Mission Orchestrator Failure

Mission Orchestrator failure shall:

```text
stop new application decisions
preserve last persisted state
allow PX4 native safety behavior
support later processing recovery
```

### 19.4 Worker Failure

Worker failure may interrupt:

```text
screening
classification
mapping
reporting
```

It shall not destabilize the aircraft.

Screening failure disables AI-generated automatic revisit planning.

### 19.5 Model Runtime Failure

A model-runtime failure shall:

```text
reject invalid output
preserve source evidence
record failure
prevent unsupported final decision
```

### 19.6 Persistence Failure

When state cannot be preserved reliably:

```text
stop creating unauditable decisions
→ use temporary local buffering where safe
→ return home if required
```

### 19.7 Vehicle Communication Failure

PX4 owns the immediate link-loss response.

PlantGuard shall:

```text
preserve last-known state
stop issuing new commands
record the interruption
wait for recovery or native failsafe outcome
```

### 19.8 Camera Failure

Camera failure may end useful inspection and trigger return-home.

It must not compromise basic vehicle stability.

## 20. Quality Attributes

### 20.1 Safety

The architecture shall ensure:

- hard blockers cannot be overridden through the dashboard;
- manual control remains available;
- PX4-native failsafes remain active;
- physical recovery requires new approval;
- no AI result directly commands the aircraft.

### 20.2 Reliability

The architecture shall ensure:

- partial data survives failure;
- valid completed work is preserved;
- mission status remains honest;
- failed jobs retain reasons;
- processing can resume.

### 20.3 Traceability

Every final result shall map to:

```text
field
mission
image
observation
site
model
configuration
timestamp
```

### 20.4 Resumability

Processing may resume from checkpoints.

Physical flight may not resume automatically.

### 20.5 Modularity

The architecture shall allow replacement of:

```text
vehicle adapter
camera adapter
model runtime
database
artifact store
job queue
dashboard implementation
```

without rewriting core mission policy.

### 20.6 Testability

Hardware-facing and model-facing dependencies shall be replaceable with:

```text
simulation adapters
recorded-data adapters
test doubles
failure injectors
```

### 20.7 Offline Operation

The complete core workflow shall operate without cloud services.

### 20.8 Performance

Long-running work shall be:

- asynchronous;
- measurable;
- profileable;
- replaceable with optimized runtimes.

### 20.9 Observability

The architecture shall record:

```text
mission state
commands
events
warnings
failures
latency
resource usage
model versions
configuration versions
```

### 20.10 Portability

ONNX Runtime remains the portable inference baseline.

TensorRT and native C++ remain planned optimization paths.

### 20.11 Usability

The farmer shall complete the normal workflow without terminal access.

## 21. Architecture Invariants

The following invariants must remain true in later design and implementation.

1. The dashboard does not directly command the vehicle.
2. AI models do not own mission state.
3. AI outputs do not bypass safety validation.
4. PX4-native safety remains active.
5. Manual control remains independent.
6. Core operation does not require cloud connectivity.
7. Ground-station-first remains the core v1.0 topology.
8. Companion deployment is optional and interface-compatible.
9. Processing is checkpointable.
10. Physical flight does not automatically resume.
11. Final results are evidence-backed and persisted.
12. Safety decisions are auditable.
13. Large artifacts move through the data plane, not mission-state messages.
14. Long-running work is asynchronous.
15. Concrete technologies remain behind stable interfaces.

## 22. Intentionally Deferred Values

This document intentionally does not freeze:

```text
final drone model
final camera model
exact network transport
exact companion computer
exact database engine
exact job queue
exact process count
exact container split
exact storage layout
exact survey altitude
exact revisit altitude
exact timing budget
exact telemetry frequency
exact model runtime location
exact authentication mechanism
exact operating-system hardening
```

These values shall be resolved later using:

```text
hardware documentation
simulation
benchmarks
field testing
security review
deployment constraints
```

## 23. Architecture Review Questions

Later Week 2 documents shall answer:

1. Which concrete component owns each responsibility?
2. Which commands and events connect the components?
3. Which interactions are synchronous?
4. Which interactions are asynchronous?
5. Where does each component run?
6. Which component owns each entity?
7. How are failures retried or escalated?
8. How are mission state and artifacts persisted?
9. How are runtime modes selected?
10. How are Week 1 requirements traced to components?

## 24. Day 1 Frozen Decisions

The following are frozen at the end of Week 2 Day 1:

1. PlantGuard UAV is local-first and offline-capable.
2. Core v1.0 is ground-station-first.
3. Companion-computer deployment is optional.
4. PX4 owns low-level flight control and native failsafes.
5. PlantGuard owns application mission policy and application safety checks.
6. Manual control remains independent of the dashboard.
7. The dashboard never communicates directly with PX4.
8. Flight, UI, persistence, model, and worker failures are isolated.
9. Control-plane and data-plane concerns are separate.
10. Immediate operator commands use synchronous acknowledgment.
11. Long-running processing uses asynchronous jobs and events.
12. Mission logic depends on stable interfaces.
13. Raw artifacts and structured state are persisted separately.
14. The dashboard is not a source of truth.
15. AI outputs are evidence, not flight commands.
16. Automatic revisit routes require safety validation.
17. Core operation has no cloud dependency or synchronization.
18. Data processing may resume from checkpoints.
19. Physical flight may not resume automatically.
20. TensorRT, native C++, and companion deployment fit behind stable interfaces.

## 25. Day 1 Acceptance Criteria

Day 1 is complete when:

- the system boundary is explicit;
- external actors are explicit;
- ground-station and drone responsibilities are separated;
- the optional companion boundary is explicit;
- logical layers are defined;
- dependency direction is defined;
- control and data planes are separated;
- synchronous and asynchronous behavior are separated;
- source-of-truth ownership is defined;
- trust boundaries are defined;
- failure boundaries are defined;
- quality attributes are defined;
- deferred values are listed;
- the architecture is ready for component decomposition.

## 26. Final Architecture Statement

PlantGuard UAV v1.0 uses a ground-station-first, local-first, layered architecture in which:

```text
the farmer expresses intent
→ the application coordinates the mission
→ application safety validates flight actions
→ hardware adapters communicate with PX4 and the camera
→ PX4 retains native flight safety
→ perception transforms imagery into evidence
→ geospatial services transform evidence into field results
→ persistence preserves state and artifacts
→ the dashboard presents the final product experience
```

The architecture is designed so that model runtimes, hardware adapters, persistence technologies, and deployment locations may evolve without rewriting the farmer workflow, mission policy, safety hierarchy, or decision contracts.
