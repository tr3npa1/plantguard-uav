# PlantGuard UAV — Runtime and Deployment Architecture

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Runtime and Deployment Architecture |
| Target release | v1.0 |
| Status | Active architecture baseline |
| Related documents | `docs/system_architecture.md`, `docs/component_catalog.md`, `docs/component_interfaces.md`, `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md`, `docs/verification_and_acceptance_plan.md`, `docs/v1_scope_baseline.md` |
| Last updated | 2026-07-21 |

## 1. Document Purpose

This document defines the runtime and deployment architecture of PlantGuard UAV v1.0.

It specifies:

- where every logical component is allowed to run;
- which components share a process in v1.0;
- which process boundaries isolate failures;
- how the drone, ground station, optional companion computer, camera, database, artifact storage, model runtimes, dashboard, and workers communicate;
- how runtime modes differ;
- how state and artifacts remain authoritative;
- how local-only synchronization works;
- startup and shutdown ordering;
- health and readiness checks;
- resource ownership;
- containerization boundaries;
- degraded-operation behavior;
- what continues and what stops when a runtime dependency fails.

This document does not define exact source-file names, operating-system package installation commands, final hardware models, exact network protocols, final database engine, or final container orchestration technology.

Those values are resolved later without violating the boundaries defined here.

## 2. Runtime Architecture Principles

### 2.1 Logical Components Are Not Automatically Services

A logical component defines ownership and behavior.

A process or service defines a runtime and failure boundary.

PlantGuard UAV shall not create one network service per logical component merely because the components are separately named.

The v1.0 design intentionally avoids unnecessary microservice complexity.

### 2.2 Ground-Station-First Is Canonical

The canonical v1.0 runtime places:

- mission workflow;
- application-level safety;
- route planning;
- persistence;
- perception;
- mapping;
- reporting;
- dashboard;
- observability;

on the ground station.

### 2.3 PX4 Remains Independently Safe

The drone and flight controller must retain:

- stabilization;
- waypoint execution;
- native geofence;
- native battery failsafe;
- native link-loss behavior;
- return-to-home;
- landing;
- manual-control priority;

without depending on the dashboard, API, worker, database, or AI model.

### 2.4 No Cloud Dependency

Core operation shall not depend on:

- cloud databases;
- cloud object storage;
- cloud queues;
- external inference APIs;
- cloud identity providers;
- cloud synchronization;
- internet connectivity.

### 2.5 Safety-Critical and Compute-Heavy Work Are Isolated

Mission-facing and flight-facing control shall not share the same failure domain as unbounded model inference or report generation.

### 2.6 Structured State and Large Artifacts Are Separated

Structured authoritative state belongs in a local relational database.

Large mission artifacts belong in mission artifact storage.

### 2.7 Local Communication Is Preferred

Ground-station processes communicate through local APIs, local IPC, local queue mechanisms, or local database coordination.

Network calls are introduced only across actual device or process boundaries.

### 2.8 Physical Flight Never Auto-Resumes

A restarted process may resume data processing from checkpoints.

A physical mission requires a new mission, preflight, and operator approval after interruption.

## 3. Runtime Nodes

PlantGuard UAV recognizes the following runtime nodes.

## 3.1 Drone / Flight-Control Node

Contains:

```text
PX4 flight controller
flight sensors
GPS
motors and propulsion
manual-control receiver
native flight mission execution
native failsafes
```

This node may also carry the RGB camera and optional companion computer physically, but those remain separate logical/runtime nodes.

## 3.2 Ground-Station Node

The primary v1.0 application node.

Contains:

```text
Farmer Dashboard
Mission API
Mission Orchestrator
Safety Supervisor
Survey Planner
Revisit Planner
Mission Data Manager
Geospatial Mapper
Report Generator
Background Job Worker
Persistence Layer
Model Registry and Metadata Manager
Observability and Event Logger
model runtimes
local database
mission artifact storage
```

## 3.3 RGB Camera Node

The camera may be:

- directly controlled by the ground station;
- controlled through the drone;
- controlled through the optional companion computer;
- triggered independently and reconciled afterward.

The Camera Manager abstracts this physical placement.

## 3.4 Optional Companion-Computer Node

A future extension that may run:

```text
camera integration
image buffering
basic image-quality validation
lightweight aerial screening
telemetry/event buffering
ONNX Runtime inference
TensorRT inference
native C++ inference
hardware monitoring
```

It does not replace PX4-native flight safety.

## 3.5 Manual-Control Node

The physical radio controller communicates with the flight controller independently of PlantGuard application services.

## 4. Canonical v1.0 Runtime Topology

```text
┌──────────────────────────────── Ground Station ────────────────────────────────┐
│                                                                                │
│  ┌────────────────┐       ┌─────────────────────────────────────────────────┐  │
│  │ Farmer         │ HTTP  │ Backend Application Process                     │  │
│  │ Dashboard      ├──────►│                                                 │  │
│  │ Process        │◄──────┤ Mission API                                     │  │
│  └────────────────┘       │ Mission Orchestrator                            │  │
│                           │ Safety Supervisor                               │  │
│                           │ Survey Planner                                  │  │
│                           │ Revisit Planner                                 │  │
│                           │ Mission Data Manager                            │  │
│                           │ application query services                      │  │
│                           └───────────────┬─────────────────────────────────┘  │
│                                           │                                    │
│                        job requests/events│                                    │
│                                           ▼                                    │
│                           ┌─────────────────────────────────────────────────┐  │
│                           │ Background Worker Process                       │  │
│                           │                                                 │  │
│                           │ Image Quality Validator                         │  │
│                           │ Aerial Health Screening Service                 │  │
│                           │ Suspicious-Site Clusterer                       │  │
│                           │ Revisit Health Reassessment Service             │  │
│                           │ PlantGuard Disease Classifier                   │  │
│                           │ Multi-Image Result Aggregator                   │  │
│                           │ Geospatial Mapper                               │  │
│                           │ Report Generator                                │  │
│                           └──────────────┬──────────────────────────────────┘  │
│                                          │                                     │
│           ┌──────────────────────────────┼───────────────────────────────┐     │
│           ▼                              ▼                               ▼     │
│  ┌──────────────────┐         ┌────────────────────┐        ┌────────────────┐│
│  │ Local Relational │         │ Mission Artifact   │        │ Logs / Metrics ││
│  │ Database         │         │ Storage            │        │ Storage        ││
│  └──────────────────┘         └────────────────────┘        └────────────────┘│
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Vehicle Integration Process                                              │  │
│  │ PX4/MAVSDK Vehicle Adapter                                               │  │
│  └───────────────────────────────┬──────────────────────────────────────────┘  │
└──────────────────────────────────┼─────────────────────────────────────────────┘
                                   │ local radio / telemetry / network link
                                   ▼
                         ┌─────────────────────┐
                         │ PX4 / Drone         │
                         │ native failsafes    │
                         │ manual control      │
                         └─────────────────────┘
```

The vehicle-integration process may initially share the backend process during simulation, but the production-oriented boundary treats it as independently isolatable.

## 5. Canonical Ground-Station Processes

## 5.1 Dashboard Process

### Contains

- Farmer Dashboard only.

### Responsibilities

- user interface;
- route-intent editing;
- mission supervision;
- result visualization.

### Communication

- communicates only with the Mission API;
- receives no direct database connection;
- receives no MAVSDK access;
- receives no direct model-runtime access.

### Failure Domain

A dashboard crash affects presentation only.

It must not terminate:

- PX4;
- manual control;
- backend mission state;
- workers;
- database;
- native return-home.

## 5.2 Backend Application Process

### Contains

- Mission API;
- Mission Orchestrator;
- Safety Supervisor;
- Survey Planner;
- Revisit Planner;
- Mission Data Manager;
- application query services;
- model-selection coordination;
- domain policies.

### Responsibilities

- synchronous API handling;
- mission-state authority;
- application safety decisions;
- workflow progression;
- route generation;
- job submission;
- event handling;
- persistence coordination.

### Excluded Work

The backend application process should not perform:

- large-batch model inference;
- long-running map generation;
- report rendering;
- unbounded image processing.

These belong to the worker process.

### Failure Domain

A backend-process failure stops:

- new dashboard commands;
- new mission-state transitions;
- new application safety decisions;
- new job submissions;
- new vehicle commands.

It does not remove:

- PX4-native behavior;
- manual control;
- already executing native failsafes;
- already persisted state;
- independently running worker checkpoints.

## 5.3 Vehicle Integration Process

### Contains

- PX4/MAVSDK Vehicle Adapter;
- telemetry normalization;
- command transport;
- connection health.

### Responsibilities

- connection to PX4;
- telemetry subscription;
- command translation;
- mission upload;
- vehicle event production.

### Reason for Isolation

MAVSDK connection handling and telemetry streams are hardware-facing and time-sensitive.

Isolation allows:

- backend restart without embedding MAVSDK state everywhere;
- telemetry-specific health checks;
- simulation replacement;
- easier failure injection;
- restricted access to vehicle-command capability.

### Communication

The backend sends validated commands to this process through a local-only interface.

The process publishes normalized vehicle events to the backend.

### Trust Rule

Only the backend application’s approved command path may invoke vehicle-control methods.

The Dashboard and workers cannot call it directly.

## 5.4 Background Worker Process

### Contains

- Background Job Worker;
- Image Quality Validator;
- Aerial Health Screening Service;
- Suspicious-Site Clusterer;
- Revisit Health Reassessment Service;
- PlantGuard Disease Classifier;
- Multi-Image Result Aggregator;
- Geospatial Mapper;
- Report Generator.

### Responsibilities

- long-running processing;
- GPU/CPU scheduling;
- retries;
- checkpoints;
- progress events;
- resource measurement.

### Failure Domain

A worker crash may stop or delay perception, mapping, or reporting.

It must not:

- change mission state directly;
- send vehicle commands;
- bypass Safety Supervisor;
- destabilize flight.

## 5.5 Local Database Process

### Purpose

Store authoritative structured state.

### Candidate v1.0 Implementations

The exact engine is deferred.

A local embedded database may be used initially.

A separate local database server may be adopted later.

### Stored Data

```text
fields
missions
mission states
route-intent records
route metadata
preflight results
safety decisions
image records
quality results
observations
suspicious sites
revisit targets
revisit results
final site results
jobs
model metadata
event/audit records
artifact references
```

### Excluded Data

Large raw images, model binaries, full rendered reports, and large GeoJSON files should not be stored as database blobs by default.

## 5.6 Mission Artifact Storage

### Purpose

Store large and file-oriented evidence.

### Stored Data

```text
raw survey images
raw revisit images
accepted/rejected manifests
telemetry exports
model artifacts
prediction artifacts
GeoJSON files
field maps
HTML reports
logs
configuration snapshots
software-version snapshots
job checkpoints
benchmark artifacts
```

### v1.0 Form

A local filesystem using the frozen mission artifact layout.

### Ownership

Mission Data Manager owns relationships and naming.

The storage implementation owns reads, writes, atomic replacement, and durability behavior.

## 5.7 Observability Runtime

### Contains

- structured log writer;
- metrics collector;
- component health records;
- mission-event log;
- local diagnostic views.

It may initially be embedded across processes with a shared local storage convention rather than a standalone service.

## 6. Logical Component Deployment Matrix

| Logical component | Ground-station backend | Ground-station worker | Vehicle process | Companion extension | Dashboard process |
|---|---:|---:|---:|---:|---:|
| Farmer Dashboard | No | No | No | No | Yes |
| Mission API | Yes | No | No | No | No |
| Mission Orchestrator | Yes | No | No | Future proxy only | No |
| Safety Supervisor | Yes | No | No | Future local guard subset | No |
| PX4/MAVSDK Vehicle Adapter | Optional in dev | No | Yes | Optional proxy | No |
| Survey Planner | Yes | Optional heavy optimization | No | Future | No |
| Camera Manager | Yes/control | No | Optional adapter | Yes where camera-attached | No |
| Mission Data Manager | Yes | Uses contract | No | Local buffer subset | No |
| Image Quality Validator | Optional small checks | Yes | No | Optional lightweight version | No |
| Aerial Health Screening Service | Optional single-image dev | Yes | No | Optional | No |
| Suspicious-Site Clusterer | No | Yes | No | Future | No |
| Revisit Planner | Yes | Optional optimization | No | Future | No |
| Revisit Health Reassessment Service | No | Yes | No | Optional | No |
| PlantGuard Disease Classifier | No | Yes | No | Optional | No |
| Multi-Image Result Aggregator | No | Yes | No | Future | No |
| Geospatial Mapper | Optional lightweight | Yes | No | No | No |
| Report Generator | No | Yes | No | No | No |
| Background Job Worker | No | Yes | No | Optional local worker | No |
| Persistence Layer | Yes | Client access | No | Local buffer only | No |
| Model Registry and Metadata Manager | Yes | Read-only client | No | Cached subset | No |
| Observability and Event Logger | Embedded/shared | Embedded/shared | Embedded/shared | Buffered subset | Dashboard reader only |

## 7. Runtime Modes

## 7.1 Simulation and Development Mode

### Purpose

Support development before real hardware is available.

### Runtime Layout

```text
Ground station/developer computer:
- PX4 SITL
- Gazebo
- MAVSDK
- backend application
- vehicle adapter
- worker
- local database
- artifact storage
- dashboard
- simulated camera or recorded images
```

### Characteristics

- all processes may run on one developer machine;
- process boundaries should still be preserved logically;
- real adapters can be replaced by simulation adapters;
- failure injection is enabled;
- no physical-flight risk exists.

### Allowed Simplifications

- backend and vehicle adapter may share a process;
- queue may be in-memory for isolated tests;
- database may be embedded;
- camera may be a replay source.

These simplifications must not alter interface semantics.

## 7.2 Ground-Station-First v1.0 Mode

### Purpose

Canonical real deployment.

### Drone

```text
PX4
flight sensors
manual-control receiver
camera hardware
native failsafes
```

### Ground Station

```text
dashboard
backend application
vehicle integration
worker
database
artifact storage
model runtimes
logs and metrics
```

### Requirements

- full mission control available locally;
- no cloud dependency;
- images and results retained locally;
- manual controller independent;
- PX4 handles immediate link-loss behavior.
- qualified image transfer, inference, and revisit decision complete inside the validated same-flight energy budget.

## 7.3 Conditionally Promoted Companion-Computer Mode

### Purpose

Reduce communication and processing latency or improve offline buffering when the ground-station path cannot pass the mandatory same-flight feasibility gate.

Companion mode is promoted into the production deployment only through controlled hardware qualification, inference-parity testing, failure analysis, security review, and field acceptance. If neither topology passes the gate, release is blocked.

### Allowed Companion Responsibilities

```text
camera control
image buffering
capture metadata association
basic image validation
lightweight aerial screening
telemetry/event buffering
hardware monitoring
ONNX Runtime inference
TensorRT inference
native C++ inference
```

### Forbidden Companion Responsibilities Without Future Architecture Approval

```text
replacing PX4 native safety
removing manual-control priority
authoritatively changing mission state
approving takeoff independently
silently replacing ground-station source of truth
performing cloud synchronization
automatically resuming physical flight
```

### Source-of-Truth Rule

In v1.0-compatible companion mode:

- the ground-station mission record remains authoritative;
- the companion maintains a local operational buffer;
- companion data is reconciled by stable IDs;
- duplicate messages are ignored;
- conflicts do not overwrite authoritative ground state automatically.

### Temporary Disconnection

During temporary disconnection:

1. PX4 continues native flight behavior.
2. The companion may continue previously authorized capture or lightweight processing.
3. The companion must not invent new mission stages.
4. Events and artifacts are buffered locally.
5. On reconnection, buffered messages replay in causal order where possible.
6. Duplicates are removed by message IDs and idempotency keys.
7. Conflicts are logged and escalated.
8. Physical-flight continuation remains governed by the existing approved mission and PX4 state.

## 7.4 Post-Flight Processing Mode

### Purpose

Enable early field testing, recovery, reprocessing, or low-bandwidth data collection.

### Flow

```text
flight captures imagery
→ flight completes and lands
→ images are transferred to ground station
→ validation runs
→ screening runs
→ sites are clustered
→ revisit planning is produced only for a future recovery mission
→ disease classification uses available revisit data
→ maps and reports are generated
```

### Important Limitation

Because processing occurs after landing, suspicious sites cannot be revisited during the same flight.

Any follow-up requires a new mission, preflight, and operator approval.

Post-flight mode does not satisfy the production v1.0 same-flight revisit requirement and cannot be used to pass the product release gate.

## 7.5 Future Optimized TensorRT / Native C++ Mode

### Purpose

Improve latency, throughput, or onboard capability.

### Allowed Implementations

```text
ONNX Runtime C++ worker
TensorRT FP16
TensorRT INT8
native C++ preprocessing
native C++ postprocessing
GPU-aware job execution
companion-side inference
```

### Compatibility Rule

Optimized runtimes must implement the same model-service contracts and preserve:

- preprocessing metadata;
- class order;
- confidence policy;
- output semantics;
- model version;
- traceability;
- failure behavior.

Optimization must not change mission policy.

## 8. Communication Boundaries

## 8.1 Dashboard to Backend

### Channel

Local HTTP/WebSocket or equivalent local application protocol.

### Allowed Data

- commands;
- queries;
- status summaries;
- warnings;
- artifact references;
- route previews;
- maps and report references.

### Forbidden

- direct SQL;
- direct filesystem mutation;
- direct MAVSDK access;
- direct worker control;
- raw model-runtime invocation.

## 8.2 Backend to Vehicle Integration

### Channel

Local-only IPC, loopback API, message bus, or equivalent isolated interface.

### Requirements

- authenticated local caller;
- command authorization context;
- safety approval reference;
- mission ID;
- idempotency key;
- command timeout;
- acknowledgment;
- event feedback.

## 8.3 Backend to Worker

### Channel

Local job queue or equivalent durable local dispatch mechanism.

### Requirements

- job ID;
- idempotency key;
- input artifact references;
- model/configuration references;
- progress;
- retry policy;
- checkpoint;
- completion event.

## 8.4 Worker to Model Runtime

The model runtime may be:

- linked in the worker process;
- isolated in a local subprocess;
- isolated in a native C++ process;
- hosted on the companion computer.

The worker remains responsible for contract validation and error normalization.

## 8.5 Processes to Database

Only approved repository interfaces may mutate structured state.

The dashboard has no direct database credentials.

Workers may update job and processing records but may not mutate mission state directly.

## 8.6 Processes to Artifact Storage

Artifact writes follow mission-scoped paths and atomic-write conventions.

Components write through a storage abstraction or Mission Data Manager rules.

## 8.7 Ground Station to Companion

### Channel

Local radio/network connection only.

### Data

- authorized capture commands;
- selected model/configuration metadata;
- artifact chunks;
- telemetry summaries;
- buffered events;
- health status.

### Prohibited

- cloud forwarding;
- unaudited state overwrite;
- direct dashboard-to-companion flight commands.

## 9. Authoritative Data Locations

| Data | Authoritative location |
|---|---|
| Vehicle operational state | PX4 telemetry / flight controller, normalized by the Vehicle Adapter |
| Mission workflow state and current activity | Ground-station relational database, owned by the Mission Orchestrator |
| Processing-job state | Ground-station relational database, owned by the responsible worker |
| Safety decisions | Ground-station relational database and event log |
| Raw images | Mission artifact storage |
| Image manifests | Artifact storage plus structured references |
| Observations | Relational database |
| Suspicious sites | Relational database |
| Revisit targets | Relational database |
| Final site results | Relational database |
| Model artifacts | Local model artifact directory |
| Model contracts | Model Registry records and snapshots |
| GeoJSON | Mission artifact storage |
| Field map | Mission artifact storage |
| HTML report | Mission artifact storage |
| Job checkpoints | Artifact storage plus job record |
| Logs | Local structured log storage |
| Metrics | Local metrics storage |
| Companion buffers | Companion local storage until reconciliation |

## 10. Database and Artifact Consistency

## 10.1 Write Ordering

For large artifacts:

1. write to a temporary mission-scoped path;
2. validate completeness;
3. atomically promote to final path;
4. persist the authoritative artifact reference;
5. emit the completion event.

## 10.2 Partial Writes

Partial artifacts are never referenced as complete.

They remain marked temporary or failed.

## 10.3 Database Failure During Artifact Write

If the artifact is complete but the database update fails:

- preserve the artifact;
- do not advertise it as authoritative;
- record a reconciliation task;
- retry persistence later.

## 10.4 Artifact Failure After Database Reservation

The structured record remains pending or failed, never complete.

## 11. Background Queue and Worker Boundary

## 11.1 v1.0 Queue Requirements

The queue technology is deferred, but it must support:

- local operation;
- durable job identity;
- duplicate-safe delivery;
- retries;
- visibility of active jobs;
- cancellation where safe;
- checkpoint references;
- bounded concurrency.

## 11.2 Queue Is Not Mission State

Queue state cannot replace authoritative workflow or processing-job state.

The Mission Orchestrator owns mission workflow state and current activity, the Vehicle Adapter derives vehicle operational state from PX4, and each worker owns its processing-job state.

## 11.3 Worker Concurrency

Concurrency is bounded by:

- CPU;
- GPU memory;
- storage bandwidth;
- model runtime limits;
- mission priority.

## 11.4 Worker Resource Classes

Recommended logical classes:

```text
cpu_light
cpu_heavy
gpu_inference
io_heavy
report_generation
```

The exact scheduler is deferred.

## 12. Model Runtime Placement

## 12.1 Portable Baseline

ONNX Runtime is the portable inference baseline.

## 12.2 Ground-Station Placement

Default v1.0 model placement:

```text
Aerial Health Screening → worker
Revisit Health Reassessment → worker
PlantGuard Disease Classification → worker
```

## 12.3 Companion Placement

Optional future placement:

```text
lightweight screening
quality validation
selected revisit inference
```

## 12.4 Runtime Isolation

A model runtime may be isolated in a subprocess when:

- native dependencies are unstable;
- GPU memory leaks must be contained;
- TensorRT/C++ is used;
- crashes must not terminate the worker coordinator.

## 12.5 Model Runtime Failure

A model-runtime crash:

- terminates only the current inference task;
- preserves input artifacts;
- records the active model/configuration;
- returns a structured failure;
- does not issue vehicle commands;
- does not force a result.

## 13. Containerization Boundaries

## 13.1 Recommended v1.0 Containers

Potential containers:

```text
dashboard
backend
vehicle_adapter
worker
database (only if server-based)
```

Artifact storage may remain a host-mounted local directory.

## 13.2 Containerization Is Not Mandatory for Flight Development

PX4 SITL, MAVSDK, GPU runtimes, and camera drivers may initially run outside containers when hardware access or debugging requires it.

## 13.3 Container Rules

- containers use explicit mounted paths;
- no container owns unique state only inside its writable layer;
- database and artifacts use persistent volumes;
- vehicle access is restricted;
- dashboard has no database or vehicle credentials;
- worker has no vehicle-control credentials;
- model artifacts are mounted read-only where practical.

## 13.4 Deployment Simplicity Rule

Do not introduce Kubernetes or distributed orchestration for v1.0.

A local process supervisor or Docker Compose-style deployment is sufficient.

## 14. Security and Trust Boundaries

## 14.1 Dashboard Boundary

The dashboard is untrusted for direct vehicle action.

All commands pass through API validation, mission state, and safety validation.

## 14.2 Vehicle Boundary

Only the vehicle-integration process possesses vehicle-command capability.

## 14.3 Worker Boundary

Workers may read artifacts and write processing results.

They cannot command the vehicle or change mission state directly.

## 14.4 Model Artifact Boundary

Model binaries and metadata are validated before activation.

## 14.5 Database Boundary

Only approved application and repository identities may mutate authoritative tables.

## 14.6 Artifact Boundary

Mission paths are scoped by mission ID and protected from path traversal or cross-mission mixing.

## 14.7 Companion Boundary

Companion messages are authenticated locally where practical and treated as replayable, duplicate-prone input.

## 15. Startup Ordering

Recommended startup sequence:

1. verify local configuration;
2. verify artifact-storage path;
3. start database;
4. apply/verify schema migrations;
5. start Observability and Event Logger;
6. start Model Registry and validate required models;
7. start Background Job Worker;
8. start Vehicle Integration Process;
9. establish PX4 connection or mark unavailable;
10. start Backend Application;
11. recover unfinished processing jobs;
12. reconstruct mission state;
13. start Dashboard;
14. expose readiness only after mandatory checks pass.

## 15.1 Startup Safety Rule

Backend startup must not automatically continue physical flight.

Any prior in-flight mission is treated as interrupted and reconciled using telemetry and safety policy.

## 16. Shutdown Ordering

Recommended controlled shutdown:

1. stop accepting new dashboard commands;
2. reject new mission creation;
3. mark application draining;
4. stop scheduling new jobs;
5. checkpoint active processing;
6. flush events and logs;
7. flush database transactions;
8. preserve artifact writes;
9. close vehicle command channel;
10. stop worker;
11. stop backend;
12. stop dashboard;
13. stop database last.

## 16.1 Flight Shutdown Rule

Do not intentionally shut down mission-control services during active flight unless:

- PX4 is already in a known safe autonomous mode;
- manual control remains available;
- operator understands the condition;
- safety policy requires it.

## 17. Health and Readiness Checks

## 17.1 Liveness

Answers:

> Is this process running?

Required for:

- dashboard;
- backend;
- vehicle integration;
- worker;
- database;
- model runtime where isolated.

## 17.2 Readiness

Answers:

> Can this process safely perform its required role?

Examples:

### Backend Ready

- database reachable;
- artifact path writable;
- model registry readable;
- required policies loaded;
- event logging functional.

### Vehicle Adapter Ready

- process healthy;
- PX4 connection established;
- telemetry current;
- command channel available.

### Worker Ready

- queue reachable;
- artifact path accessible;
- required runtime available;
- enough local resources.

### Model Ready

- model artifact valid;
- metadata valid;
- input/output contract valid;
- runtime initialized.

## 17.3 Mission Readiness Is Separate

Process readiness does not equal mission preflight PASS.

Technical preflight evaluates:

- field;
- route;
- vehicle;
- camera;
- battery;
- GPS;
- storage;
- models;
- the dry-daylight production environment;
- operator supervision and manual-control readiness.

Operator approval is evaluated after technical preflight and is linked to that snapshot. Final takeoff authorization revalidates current telemetry and matching route/configuration versions immediately before arming.

## 18. Resource Ownership

## 18.1 GPU

The worker or dedicated model-runtime process owns GPU scheduling.

The backend must not run unbounded GPU inference.

## 18.2 Vehicle Connection

The Vehicle Integration Process owns the MAVSDK/PX4 connection.

## 18.3 Camera Connection

The Camera Manager owns the camera-control session, whether implemented on ground or companion.

## 18.4 Database Migrations

Only one startup/migration owner performs schema migrations.

## 18.5 Artifact Writes

Mission-scoped locks or atomic conventions prevent competing writes to the same artifact.

## 18.6 Model Activation

Model Registry and Metadata Manager owns the active-model assignment.

Workers consume a versioned snapshot.

## 19. Failure Domains and Degraded Operation

## 19.1 Dashboard Failure

### Continues

- PX4 native safety;
- manual control;
- backend mission state;
- vehicle integration;
- workers;
- persistence;
- logging.

### Stops or Degrades

- farmer visualization;
- new dashboard commands;
- interactive route editing.

### Recovery

Restart dashboard and reconstruct view from API state.

## 19.2 Mission API Failure

### Continues

- PX4 native safety;
- manual control;
- vehicle adapter;
- existing backend-internal workflows if process remains healthy;
- workers already executing jobs.

### Stops

- new dashboard commands;
- new external queries.

### Recovery

Restore API endpoint without automatically restarting flight stages.

## 19.3 Backend Application Failure

### Continues

- PX4 native behavior;
- manual control;
- native return-home;
- vehicle process telemetry buffering where configured;
- active worker checkpointing;
- persisted state.

### Stops

- new application decisions;
- new safety decisions;
- new job scheduling;
- new vehicle commands.

### Recovery

Reconstruct state from database and events. Never auto-resume physical flight.

## 19.4 Mission Orchestrator Failure

Equivalent to backend workflow failure:

- no new state transitions;
- no new mission actions;
- current PX4 behavior remains authoritative;
- operator/manual control remains available;
- processing can resume later;
- physical continuation requires recovery policy.

## 19.5 Safety Supervisor Failure

### Rule

New application flight actions are blocked.

### Continues

- PX4-native safety;
- manual control;
- current native failsafe behavior.

### Stops

- takeoff approval;
- new survey-route approval;
- revisit approval;
- new recovery authorization.

## 19.6 Vehicle Integration Failure

### Continues

- PX4-native safety;
- manual control;
- flight controller’s configured link-loss behavior.

### Stops

- application vehicle commands;
- normalized telemetry delivery;
- camera coordination that depends on ground telemetry.

### Recovery

Reconnect and reconcile current PX4 state. Do not assume previous application state is still valid.

## 19.7 Telemetry-Link Failure

PX4 performs immediate native link-loss behavior.

PlantGuard:

- marks telemetry stale;
- stops new commands;
- preserves last known state;
- warns operator;
- records link loss;
- reconciles after recovery.

## 19.8 Camera Failure

### Continues

- stable flight;
- PX4 safety;
- return-home;
- manual control.

### Stops or Degrades

- useful inspection capture;
- perception from missing imagery;
- revisit evidence.

Repeated/global camera failure normally triggers return-home according to safety policy.

## 19.9 Worker Failure

### Continues

- flight;
- mission-state service;
- vehicle integration;
- dashboard;
- persistence.

### Stops or Degrades

- image validation;
- screening;
- clustering;
- classification;
- mapping;
- reporting.

### Mission Effect

Screening failure disables AI-generated automatic revisit planning.

## 19.10 Model Runtime Failure

### Continues

- flight safety;
- raw capture;
- evidence storage;
- unrelated processing.

### Stops

- affected inference task.

### Recovery

Retry from checkpoint or use later processing. Do not force a prediction.

## 19.11 Database Failure

### Continues

- PX4-native safety;
- manual control;
- safe return behavior;
- temporary buffering where explicitly supported.

### Stops

- new unauditable decisions;
- authoritative mission-state mutation;
- reliable new job creation;
- final-result publication.

### Mission Effect

Return-home is favored when state integrity cannot be maintained.

## 19.12 Artifact-Storage Failure

### Continues

- PX4-native safety;
- manual control;
- telemetry where separately stored.

### Stops or Degrades

- reliable image retention;
- model input processing;
- map/report output;
- evidence traceability.

A camera mission should not continue indefinitely when images cannot be retained.

## 19.13 Observability Failure

Local fallback logging is attempted.

Persistent inability to record required safety/audit decisions causes degraded readiness or mission blocking.

## 19.14 Companion-Computer Failure

### Continues

- PX4-native flight safety;
- manual control;
- ground-station workflow where connectivity exists;
- already uploaded PX4 route.

### Stops or Degrades

- companion camera control;
- onboard buffering;
- onboard inference;
- companion health monitoring.

### Recovery

Ground station uses buffered/reconciled data if available. No automatic mission-stage invention occurs.

## 19.15 Ground-Station Power Failure

### Continues

- PX4-native flight behavior;
- manual control;
- configured link-loss failsafe;
- companion buffering where present.

### Stops

- dashboard;
- backend;
- workers;
- database access;
- ground-station model inference.

### Recovery

After restart:

- recover database/artifact integrity;
- reconcile with PX4;
- do not auto-resume physical flight;
- create recovery mission where needed.

## 20. Failure-Continuation Matrix

| Failure | Native flight safety | Manual control | New vehicle commands | New AI work | Existing AI checkpoint | Dashboard |
|---|---:|---:|---:|---:|---:|---:|
| Dashboard | Yes | Yes | Backend-dependent | Yes | Yes | No |
| API only | Yes | Yes | Internal only | Yes | Yes | Unavailable |
| Backend | Yes | Yes | No | No new jobs | Preserved | Stale |
| Safety Supervisor | Yes | Yes | No new flight action | Non-flight jobs possible | Preserved | Warning |
| Vehicle adapter | Yes | Yes | No | Possible post-flight | Preserved | Stale telemetry |
| Worker | Yes | Yes | Yes through backend | No | Preserved | Available |
| Model runtime | Yes | Yes | Yes | Affected model only | Preserved | Available |
| Database | Yes | Yes | Safe return only as policy allows | No authoritative new work | Local temporary only | Degraded |
| Artifact storage | Yes | Yes | Safe return favored | No evidence-dependent work | At risk | Degraded |
| Telemetry link | PX4 native | Yes | No | Existing local only | Preserved | Stale |
| Camera | Yes | Yes | Return/land available | Existing images only | Preserved | Warning |
| Companion | Yes | Yes | Ground path if available | Ground path if available | Buffered | Available |
| Ground-station power | PX4 native | Yes | No | No | Disk-dependent | No |

## 21. Simulation Adapters

The following production interfaces require simulation implementations:

```text
VehicleControl
VehicleTelemetry
CameraControl
ArtifactStorage
MissionRepository
ModelRuntime
WeatherInput
Clock
```

Simulation adapters must emit the same commands, events, errors, and identifiers as real adapters.

## 22. Deployment Configuration Profiles

Recommended logical profiles:

```text
development
simulation
ground_station_v1
post_flight
companion_experimental
optimized_cpp
```

Each profile defines:

- enabled processes;
- adapters;
- model runtimes;
- storage roots;
- queue backend;
- logging level;
- hardware endpoints;
- safety policy profile.

Safety-critical values remain versioned and captured in the mission configuration snapshot.

## 23. Network and Port Exposure Rules

- dashboard is exposed only to the local operator network;
- backend API is local-network or loopback scoped;
- vehicle integration is not publicly exposed;
- database is not exposed beyond the local deployment;
- worker control is local only;
- companion link is local only;
- no inbound internet access is required;
- no public cloud endpoint is required.

Exact ports and protocols are deferred.

## 24. Backup and Retention

## 24.1 Mission Evidence

Raw imagery is retained by default until operator deletion or retention policy.

## 24.2 Database Backup

Local database backup is required before destructive migrations and before major field-test campaigns.

## 24.3 Mission Export

A mission must be exportable as a self-contained artifact set with:

- structured summary;
- manifests;
- images;
- GeoJSON;
- reports;
- configuration;
- model metadata;
- software version;
- logs.

## 24.4 Companion Buffers

Companion buffers may be deleted only after confirmed ground-station reconciliation.

## 25. Runtime Invariants

The following must remain true:

1. The dashboard never possesses vehicle-control capability.
2. Workers never possess vehicle-control capability.
3. PX4-native safety does not depend on application processes.
4. Mission state is authoritative on the ground station.
5. Companion state is buffered/cached unless a future baseline changes authority.
6. Structured records and large artifacts remain separate.
7. Long-running inference does not block the API process.
8. A worker crash does not crash vehicle integration.
9. A dashboard crash does not crash mission control.
10. A model crash does not force a prediction.
11. A database failure stops new unauditable decisions.
12. Physical flight never auto-resumes after process restart.
13. No cloud service is required.
14. Optimized runtimes preserve existing contracts.
15. Manual control remains independent.

## 26. Intentionally Deferred Runtime Decisions

The following are not frozen yet:

```text
exact database engine
exact queue implementation
exact process supervisor
exact container runtime
exact IPC protocol
exact network transport to PX4
exact camera transport
exact companion hardware
exact GPU model
exact CPU/GPU concurrency
exact port assignments
exact authentication mechanism
exact encryption mechanism
exact telemetry sampling rate
exact checkpoint interval
exact artifact-retention duration
```

These must be resolved later through simulation, hardware selection, performance testing, and security review.

## 27. Frozen Runtime Decisions

1. Ground-station-first is the canonical v1.0 deployment.
2. Logical components do not automatically become network services.
3. The dashboard, backend, vehicle integration, and worker are separate runtime concerns.
4. The backend owns mission workflow and application safety.
5. The worker owns long-running perception, mapping, and reporting execution.
6. The vehicle-integration process is the only application runtime with vehicle-command capability.
7. Structured state belongs in a local relational database.
8. Large mission artifacts belong in local mission artifact storage.
9. The dashboard has no direct database, worker, model, or vehicle access.
10. The worker has no vehicle-command capability.
11. The companion computer is conditional: unnecessary when the ground path passes the same-flight gate, but formally promoted when required to pass it.
12. The companion may buffer, capture, validate, and infer, but does not replace PX4 safety.
13. The ground-station mission record remains authoritative in v1.0-compatible companion mode.
14. Companion synchronization is local-only and duplicate-safe.
15. Cloud dependency and cloud synchronization are excluded.
16. Post-flight processing is a supported recovery and validation mode, not a substitute for same-flight revisit release behavior.
17. Post-flight revisit requires a new mission.
18. ONNX Runtime is the portable baseline.
19. TensorRT and native C++ are compatible optimization modes.
20. Model runtimes may be isolated in subprocesses.
21. Long-running work uses a local durable queue abstraction.
22. Queue state does not replace authoritative workflow or processing-job state.
23. Startup never auto-resumes physical flight.
24. Shutdown preserves checkpoints, events, transactions, and artifacts.
25. Process readiness is separate from mission preflight.
26. Database failure stops new unauditable decisions.
27. Worker/model failure does not destabilize flight.
28. PX4 handles immediate telemetry/link-loss safety.
29. Manual control remains independent.
30. Kubernetes or distributed cloud orchestration is unnecessary for v1.0.

## 28. Runtime-Architecture Acceptance Criteria

The runtime-architecture baseline is complete when:

- every logical component has an allowed runtime location;
- runtime modes are defined;
- ground-station process boundaries are explicit;
- vehicle, worker, database, storage, and dashboard boundaries are explicit;
- optional companion responsibilities are bounded;
- source-of-truth rules are explicit;
- local-only synchronization behavior is explicit;
- model-runtime placement is explicit;
- containerization boundaries are explicit;
- startup and shutdown ordering are explicit;
- health and readiness checks are explicit;
- resource ownership is explicit;
- failure domains and degraded behavior are explicit;
- no safety-critical behavior depends on the dashboard, AI, or cloud;
- physical flight cannot automatically resume;
- the architecture is ready for mission-sequence definition and review.

## 29. Final Runtime Statement

PlantGuard UAV v1.0 uses a local, ground-station-first runtime in which:

```text
the dashboard captures farmer intent
→ the backend owns workflow and application safety
→ the vehicle integration process communicates with PX4
→ the worker performs long-running perception and reporting
→ the database stores authoritative structured state
→ artifact storage preserves mission evidence
→ PX4 retains native flight safety
```

Optional companion, TensorRT, and native C++ deployments may improve performance or resilience, but they must remain compatible with the same mission, safety, traceability, and failure-isolation contracts.
