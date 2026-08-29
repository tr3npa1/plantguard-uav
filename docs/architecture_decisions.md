# PlantGuard UAV — Architecture Decisions

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Architecture Decisions |
| Target release | v1.0 |
| Status | Active architecture baseline |
| Related documents | `docs/system_architecture.md`, `docs/component_catalog.md`, `docs/component_interfaces.md`, `docs/runtime_and_deployment_architecture.md`, `docs/mission_sequence_flows.md`, `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md`, `docs/verification_and_acceptance_plan.md`, `docs/v1_scope_baseline.md` |
| Last updated | 2026-07-21 |

## 1. Document Purpose

This document records the major architectural decisions for PlantGuard UAV v1.0.

Each decision captures:

- context;
- chosen approach;
- rationale;
- considered alternatives;
- consequences;
- risks;
- mitigations;
- conditions for revisiting the decision;
- affected components;
- affected documents.

The purpose of this document is to prevent future implementation choices from silently contradicting the approved architecture.

## 2. Decision Statuses

```text
proposed
accepted
superseded
deprecated
rejected
```

All decisions in this document are `accepted` unless explicitly stated otherwise.

## 3. Decision Index

| ID | Decision |
|---|---|
| ADR-001 | Use a ready-made PX4-capable drone |
| ADR-002 | Use MAVSDK as the primary application-level vehicle interface |
| ADR-003 | Use ROS 2 selectively |
| ADR-004 | Operate local-first and offline-capable |
| ADR-005 | Use a ground-station-first v1.0 topology |
| ADR-006 | Gate companion-computer deployment on same-flight feasibility |
| ADR-007 | Separate PX4 native safety from PlantGuard application safety |
| ADR-008 | Use FastAPI for the mission-facing API |
| ADR-009 | Use asynchronous workers for long-running processing |
| ADR-010 | Use relational persistence for structured state |
| ADR-011 | Use mission artifact storage for large evidence |
| ADR-012 | Use GeoJSON for geospatial exchange |
| ADR-013 | Use ONNX Runtime as the portable inference baseline |
| ADR-014 | Treat TensorRT and native C++ as compatible optimization extensions |
| ADR-015 | Exclude cloud synchronization from v1.0 |
| ADR-016 | Never automatically resume physical flight |
| ADR-017 | Separate farmer route intent from executable route generation |
| ADR-018 | Separate planning, safety approval, and route execution |
| ADR-019 | Separate per-image model evidence from final site decisions |
| ADR-020 | Keep ground-station mission state authoritative |
| ADR-021 | Do not convert every logical component into a microservice |
| ADR-022 | Use a local durable queue abstraction |
| ADR-023 | Support post-flight processing |
| ADR-024 | Separate structured state from file-oriented artifacts |
| ADR-025 | Preserve immutable events and explicit corrections |
| ADR-026 | Use versioned model and preprocessing contracts |
| ADR-027 | Treat dashboard state as derived, not authoritative |
| ADR-028 | Preserve partial evidence and honest unresolved outcomes |
| ADR-029 | Use recovery missions rather than reactivating interrupted flights |
| ADR-030 | Keep cloud and internet connectivity outside the safety path |
| ADR-031 | Separate workflow, mission activity, vehicle, and job state |
| ADR-032 | Separate technical preflight, operator approval, and final takeoff authorization |

# ADR-001 — Use a Ready-Made PX4-Capable Drone

## Status

Accepted.

## Context

The product goal is to deliver and operate a field-qualified autonomous inspection system with auditable ML, geospatial reasoning, deployment controls, and validation evidence.

Designing a custom airframe, motor system, ESC stack, flight controller, stabilization system, and low-level control stack would consume substantial delivery capacity and introduce unnecessary safety risk.

## Decision

PlantGuard UAV v1.0 will use a ready-made programmable drone or compatible platform capable of running PX4 and supporting MAVSDK-based mission control.

## Rationale

- keeps the project focused on software and ML systems;
- reduces hardware integration risk;
- preserves access to mature flight-control and failsafe behavior;
- supports PX4 SITL before hardware purchase;
- supports an evidence-driven path from integration through field validation and production deployment;
- improves reproducibility and maintainability.

## Alternatives Considered

### Custom airframe and flight-control stack

Rejected for v1.0 because it would expand scope into:

- flight dynamics;
- stabilization;
- PCB/electrical design;
- motor/ESC tuning;
- safety certification concerns;
- extensive hardware testing.

### Proprietary drone without programmable mission control

Rejected because it could block:

- route upload;
- telemetry access;
- mission automation;
- application-level safety integration;
- reproducible simulation.

## Consequences

Positive:

- faster software progress;
- safer baseline;
- simulation/real-vehicle consistency;
- stronger focus on autonomy and ML systems.

Negative:

- hardware capabilities depend on selected platform;
- weather rating and payload capacity remain constrained;
- some low-level behavior cannot be customized.

## Risks and Mitigations

Risk: selected platform lacks required camera or telemetry integration.

Mitigation: complete a hardware compatibility review before purchase.

Risk: proprietary platform changes APIs.

Mitigation: prefer standards-compatible PX4/MAVSDK integration.

## Revisit Conditions

Revisit only if no available PX4-capable platform satisfies:

- payload;
- camera;
- flight time;
- programmability;
- safety;
- legal operation;
- budget.

## Affected Components

- PX4/MAVSDK Vehicle Adapter;
- Camera Manager;
- Safety Supervisor;
- Survey Planner;
- Revisit Planner.

## Affected Documents

- `docs/system_scope.md`
- `docs/system_architecture.md`
- `docs/runtime_and_deployment_architecture.md`

# ADR-002 — Use MAVSDK as the Primary Application-Level Vehicle Interface

## Status

Accepted.

## Context

PlantGuard needs to:

- connect to PX4;
- read telemetry;
- arm;
- take off;
- upload missions;
- start missions;
- pause/hold;
- return home;
- land.

The application needs a stable interface above raw MAVLink message handling.

## Decision

MAVSDK will be the primary application-level vehicle-control and telemetry interface.

## Rationale

- purpose-built for application-level PX4 integration;
- supports telemetry and mission control;
- reduces direct MAVLink complexity;
- works with PX4 SITL;
- supports clear adapter boundaries;
- fits Python-first development.

## Alternatives Considered

### Direct MAVLink

Rejected as the primary interface because it increases protocol complexity and safety-sensitive implementation burden.

### ROS 2-only control path

Rejected as mandatory because the project does not need every vehicle interaction to pass through ROS 2.

### Proprietary vendor SDK

Rejected unless hardware selection later makes it unavoidable and compatible with the adapter contract.

## Consequences

Positive:

- faster development;
- simpler tests;
- clear Vehicle Adapter boundary.

Negative:

- behavior is limited by MAVSDK capabilities;
- some specialized features may require lower-level integration.

## Risks and Mitigations

Risk: a needed PX4 feature is not exposed.

Mitigation: permit narrowly scoped lower-level MAVLink access behind the Vehicle Adapter.

## Revisit Conditions

- required feature unavailable in MAVSDK;
- performance or reliability evidence shows MAVSDK is insufficient;
- selected platform requires a different interface.

## Affected Components

- PX4/MAVSDK Vehicle Adapter;
- Safety Supervisor;
- Mission Orchestrator.

## Affected Documents

- `docs/component_catalog.md`
- `docs/component_interfaces.md`

# ADR-003 — Use ROS 2 Selectively

## Status

Accepted.

## Context

ROS 2 offers:

- messaging;
- lifecycle management;
- robotics tooling;
- simulation integration;
- distributed-node support.

However, requiring every PlantGuard component to run as a ROS 2 node would increase complexity.

## Decision

ROS 2 may be used where it provides clear value, such as:

- simulation integration;
- companion-computer robotics integration;
- hardware drivers;
- future sensor fusion;
- specialized autonomy extensions.

It will not be a mandatory wrapper around every backend, perception, persistence, or dashboard component.

## Rationale

- avoids unnecessary framework coupling;
- keeps FastAPI/backend workflows simple;
- preserves use of ROS 2 for robotics-specific concerns;
- avoids turning application services into robotics nodes without need.

## Alternatives Considered

### Everything as ROS 2 nodes

Rejected because it would complicate:

- API integration;
- persistence;
- jobs;
- dashboard communication;
- testing;
- deployment.

### No ROS 2 anywhere

Rejected because ROS 2 may be useful for later companion or robotics integration.

## Consequences

- mixed architecture must be documented clearly;
- bridges may be required where ROS 2 and application services meet;
- ROS 2 becomes an extension tool rather than the application backbone.

## Risks and Mitigations

Risk: duplicated messaging concepts.

Mitigation: preserve canonical command/event semantics independent of transport.

## Revisit Conditions

Revisit if:

- companion deployment becomes central;
- multiple sensors require ROS 2 tooling;
- a robotics subsystem gains enough complexity to justify ROS 2 ownership.

# ADR-004 — Operate Local-First and Offline-Capable

## Status

Accepted.

## Context

Agricultural fields may have unreliable or unavailable internet connectivity.

Core flight, capture, inference, storage, and reporting must remain available locally.

## Decision

PlantGuard UAV v1.0 will operate fully on local infrastructure.

## Rationale

- reliable field operation;
- predictable latency;
- improved privacy;
- no external-service dependency;
- simpler release scope;
- safer failure behavior.

## Alternatives Considered

### Cloud-first backend

Rejected because internet availability cannot be assumed.

### Hybrid mandatory cloud synchronization

Rejected for v1.0 due to complexity and weak field reliability.

## Consequences

Positive:

- self-contained system;
- offline operation;
- no recurring cloud requirement.

Negative:

- local backup and storage management are required;
- remote fleet management is deferred.

## Risks and Mitigations

Risk: ground-station storage loss.

Mitigation: backups, mission exports, retention policy, and integrity checks.

## Revisit Conditions

Cloud export may be considered later as a non-blocking optional extension.

# ADR-005 — Use a Ground-Station-First v1.0 Topology

## Status

Accepted.

## Context

Onboard inference introduces:

- hardware cost;
- thermal constraints;
- power constraints;
- GPU/driver complexity;
- deployment complexity;
- additional failure modes.

## Decision

Mission orchestration, application safety, perception, persistence, mapping, reporting, and dashboard services run primarily on the ground station.

## Rationale

- easier debugging;
- stronger compute;
- simpler model iteration;
- reduced payload and power demand;
- avoids companion hardware when the ground path meets the qualified same-flight timing and energy gate;
- preserves post-flight processing as a recovery path, not as a substitute for the mandatory same-flight revisit workflow.

## Alternatives Considered

### Onboard-first inference

Rejected as the mandatory v1.0 architecture.

### Cloud inference

Rejected because core operation must be offline.

## Consequences

- communication quality affects same-flight analysis;
- post-flight processing remains available for recovery and reprocessing;
- onboard processing is promoted only through the feasibility gate.

## Risks and Mitigations

Risk: link bandwidth prevents same-flight image transfer.

Mitigation:

- buffer images;
- use lower-resolution previews;
- qualify a companion capture/inference path;
- block production release if no topology meets the same-flight gate.

## Revisit Conditions

Revisit after field measurements of:

- transfer bandwidth;
- inference latency;
- mission timing;
- battery;
- companion feasibility.

# ADR-006 — Gate Companion-Computer Deployment on Same-Flight Feasibility

## Status

Accepted.

## Decision

Ground-station-first is the default topology. Companion deployment is not mandatory when measured transfer, inference, revisit-decision, return, landing, and reserve timing passes on the selected ground path.

If the ground path fails that gate, v1.0 must either qualify a compatible companion path through formal change control or block production release. The same-flight revisit requirement shall not be weakened into post-flight-only processing to avoid the gate.

## Rationale

- avoids premature hardware coupling;
- keeps architecture portable;
- supports later onboard buffering and inference;
- preserves ground-station baseline.

## Allowed Responsibilities

- camera control;
- buffering;
- lightweight quality validation;
- lightweight screening;
- event buffering;
- ONNX Runtime;
- TensorRT;
- native C++ inference.

## Prohibited Responsibilities Without Future Approval

- replacing PX4-native failsafes;
- independently approving takeoff;
- silently taking authoritative mission ownership;
- automatic physical-flight resume;
- cloud synchronization.

## Promotion Conditions

Promote companion deployment when controlled measurements show that the ground path cannot produce the approved revisit decision within the validated communication and energy budget. Promotion requires hardware qualification, parity testing, failure analysis, local authentication, and field acceptance evidence.

# ADR-007 — Separate PX4 Native Safety From PlantGuard Application Safety

## Status

Accepted.

## Context

Low-level flight safety and high-level mission safety have different responsibilities and timing requirements.

## Decision

PX4 owns:

- stabilization;
- low-level control;
- native geofence;
- battery failsafes;
- link-loss behavior;
- return-home execution;
- landing;
- manual-control priority.

PlantGuard Safety Supervisor owns:

- preflight;
- route validation;
- application battery feasibility;
- weather policy;
- revisit feasibility;
- recovery authorization.

## Rationale

- preserves mature flight-controller safety;
- prevents backend or AI failure from destabilizing flight;
- supports clear testing;
- avoids reimplementing low-level safety.

## Alternatives Considered

### Application owns all safety

Rejected as unsafe and unnecessary.

### PX4 owns all mission policy

Rejected because PX4 does not understand PlantGuard-specific revisit, image, model, storage, and workflow requirements.

## Consequences

- both safety layers must remain consistent;
- application safety can be stricter than PX4;
- native failsafes always remain active.

## Risks and Mitigations

Risk: contradictory safety decisions.

Mitigation: native PX4 action remains authoritative for immediate flight behavior.

# ADR-008 — Use FastAPI for the Mission-Facing API

## Status

Accepted.

## Context

The system needs a local API for:

- dashboard commands;
- mission status;
- route intent;
- evidence retrieval;
- report retrieval.

## Decision

FastAPI will be the primary mission-facing backend API framework.

## Rationale

- typed Python integration;
- automatic API documentation;
- async support;
- good compatibility with Pydantic;
- suitable for local service deployment;
- aligns with existing PlantGuard experience.

## Alternatives Considered

### Flask

Viable but less aligned with typed contracts and async workflows.

### Django

More framework than required for the mission API.

### ROS 2 services as the dashboard API

Rejected because the farmer interface should not depend directly on robotics middleware.

## Consequences

- API schemas must remain separate from domain entities;
- long-running work must not run directly inside request handlers;
- explicit startup/readiness behavior is required.

# ADR-009 — Use Asynchronous Workers for Long-Running Processing

## Status

Accepted.

## Decision

Image validation, screening, clustering, revisit analysis, classification, aggregation, mapping, reporting, and reprocessing run as asynchronous jobs.

## Rationale

- prevents API blocking;
- supports retries;
- supports progress;
- supports checkpoints;
- isolates model crashes;
- allows resource scheduling.

## Alternatives Considered

### Run everything inside API requests

Rejected due to timeouts, poor failure isolation, and weak resumability.

### One blocking mission script

Rejected for production architecture, though a CLI orchestrator may still be useful for testing.

## Consequences

- job identity and idempotency are required;
- queue state and mission state must remain separate;
- failure reconciliation becomes explicit.

# ADR-010 — Use Relational Persistence for Structured State

## Status

Accepted.

## Decision

Fields, missions, states, images, observations, sites, results, jobs, safety decisions, and references use relational persistence.

## Rationale

- structured relationships;
- transactions;
- integrity constraints;
- traceable queries;
- migrations;
- strong fit for mission entities.

## Alternatives Considered

### Store all state in JSON files

Rejected as the primary authoritative state because transactions and relationships would be fragile.

### NoSQL document database

Not required for v1.0 and offers weaker value for the strongly related domain model.

## Consequences

- schema migrations are required;
- relational modeling must be maintained;
- large files should remain outside the database.

# ADR-011 — Use Mission Artifact Storage for Large Evidence

## Status

Accepted.

## Decision

Raw images, model binaries, prediction artifacts, GeoJSON, logs, maps, reports, checkpoints, and snapshots are stored in mission-scoped artifact storage.

## Rationale

- efficient file access;
- natural evidence organization;
- exportable missions;
- avoids database blobs;
- preserves original evidence.

## Alternatives Considered

### Store everything in database blobs

Rejected due to operational complexity and poor portability.

### Cloud object storage

Rejected as a core dependency.

## Consequences

- atomic-write conventions are required;
- database references and artifacts must be reconciled;
- retention and backup policies are required.

# ADR-012 — Use GeoJSON for Geospatial Exchange

## Status

Accepted.

## Decision

GeoJSON is the canonical exchange format for:

- field boundaries;
- exclusions;
- routes;
- observations;
- sites;
- revisit targets;
- final results;
- coverage geometry.

## Rationale

- human-readable;
- widely supported;
- web-map compatible;
- suitable for artifact export;
- easy to validate and inspect.

## Alternatives Considered

### Custom coordinate JSON

Rejected because it would duplicate an established standard.

### Shapefile as primary exchange format

Rejected due to multi-file packaging and weaker web integration.

## Consequences

- persisted GeoJSON uses WGS 84 / EPSG:4326 and `[longitude, latitude]` axis order;
- metric calculations use a mission-recorded local projected CRS in metres;
- AGL and AMSL altitude fields and their sources remain explicit and non-interchangeable;
- UTC wall-clock, monotonic capture time, and PX4 clock mapping are preserved;
- very large datasets may require optimized derived formats later.

# ADR-013 — Use ONNX Runtime as the Portable Inference Baseline

## Status

Accepted.

## Decision

ONNX Runtime is the portable deployment baseline for screening, reassessment, and classification models.

## Rationale

- portable across CPU/GPU environments;
- supports Python and C++;
- enables model-runtime separation;
- fits later optimization;
- avoids permanent coupling to training framework.

## Alternatives Considered

### PyTorch-only production inference

Retained for training/reference but not the portability baseline.

### TensorRT-only deployment

Rejected as the baseline due to NVIDIA-specific requirements.

## Consequences

- ONNX export and parity tests are mandatory;
- preprocessing and output contracts must be versioned;
- unsupported operations must be identified.

# ADR-014 — Treat TensorRT and Native C++ as Compatible Optimization Extensions

## Status

Accepted.

## Decision

TensorRT FP16/INT8 and native C++ inference are planned performance extensions that implement existing model contracts.

## Rationale

- provides a qualified performance-optimization path;
- improves latency and throughput;
- supports companion deployment;
- preserves portable baseline.

## Consequences

- parity testing is required;
- optimization cannot change business semantics;
- optimized runtimes must preserve metadata and traceability.

## Revisit Conditions

Activate after portable baseline correctness is established.

# ADR-015 — Exclude Cloud Synchronization From v1.0

## Status

Accepted.

## Decision

No automatic cloud upload, cloud state synchronization, or cloud database is part of v1.0.

## Rationale

- offline reliability;
- reduced scope;
- lower security burden;
- simpler data ownership;
- no recurring dependency.

## Consequences

- local mission export is required;
- optional cloud sync may be considered later as a separate extension.

# ADR-016 — Never Automatically Resume Physical Flight

## Status

Accepted.

## Decision

Process restart, worker restart, database recovery, or telemetry reconnection must never automatically continue a prior physical mission.

## Rationale

- physical conditions may have changed;
- operator awareness may be lost;
- route validity may have expired;
- battery and weather may differ;
- state reconciliation may be incomplete.

## Required Recovery

- new mission;
- new preflight;
- new operator approval;
- explicit recovery scope.

## Consequences

- some missions remain partial;
- data processing may resume independently.

# ADR-017 — Separate Farmer Route Intent From Executable Route Generation

## Status

Accepted.

## Decision

The v1.0 Farmer Dashboard captures automatic coverage confirmation and approved exclusion zones only. Sweep direction, altitude, speed, overlap, and coverage density come from versioned, safety-reviewed mission configuration.

The Survey Planner converts that intent into a candidate executable route.

## Rationale

Farmer input should be flexible without allowing unsafe direct waypoint control.

## Alternatives Considered

### Dashboard generates PX4 waypoints directly

Rejected due to safety, validation, coverage, and battery concerns.

### Priority zones, guided routes, and custom route drafts

Deferred beyond v1.0 because they expand authorization, validation, usability, and field-acceptance scope. Exclusion zones remain mandatory.

## Consequences

- route intent remains a minimal versioned contract;
- skipped coverage must be disclosed;
- unsupported customization is rejected explicitly.

# ADR-018 — Separate Planning, Safety Approval, and Route Execution

## Status

Accepted.

## Decision

```text
Planner
→ proposes route

Safety Supervisor
→ approves/restricts/rejects route

Vehicle Adapter
→ executes approved route
```

## Rationale

This prevents one component from proposing, approving, and executing its own flight plan.

## Consequences

- more explicit contracts;
- stronger testing;
- safer failure isolation;
- additional state records.

# ADR-019 — Separate Per-Image Model Evidence From Final Site Decisions

## Status

Accepted.

## Decision

Health and disease services produce per-image evidence.

The Multi-Image Result Aggregator produces the final site result.

## Rationale

- multiple views may disagree;
- image quality varies;
- model confidence alone is insufficient;
- uncertainty must be preserved;
- final status requires cross-image policy.

## Consequences

- per-image evidence is retained;
- aggregation policy must be versioned;
- final result becomes reproducible.

# ADR-020 — Keep Ground-Station Mission State Authoritative

## Status

Accepted.

## Decision

In v1.0 and compatible companion mode, the ground-station mission record remains authoritative.

The companion stores local buffers and cached state only.

## Rationale

- prevents split-brain mission control;
- simplifies reconciliation;
- keeps dashboard and persistence consistent;
- preserves optional companion deployment.

## Consequences

- temporary disconnection requires buffering;
- companion conflicts cannot silently overwrite ground state;
- future onboard-first mode would require a new architecture decision.

# ADR-021 — Do Not Convert Every Logical Component Into a Microservice

## Status

Accepted.

## Decision

Logical boundaries remain explicit, but v1.0 groups components into a small number of processes:

- Dashboard;
- Backend;
- Vehicle Integration;
- Worker;
- Database where applicable.

## Rationale

- reduces deployment complexity;
- avoids network overhead;
- simplifies local operation;
- preserves testable modularity.

## Alternatives Considered

### One service per component

Rejected as unnecessary operational complexity.

### One monolithic process for everything

Rejected because vehicle and worker failures require isolation.

# ADR-022 — Use a Local Durable Queue Abstraction

## Status

Accepted.

## Decision

Long-running jobs use a local durable queue abstraction.

The exact implementation remains deferred.

## Requirements

- job identity;
- duplicate-safe delivery;
- retries;
- checkpoints;
- bounded concurrency;
- local operation.

## Rule

Queue state is not authoritative mission state.

## Consequences

- implementation can start simple;
- later queue replacement does not alter mission semantics.

# ADR-023 — Support Post-Flight Processing

## Status

Accepted.

## Decision

PlantGuard supports missions where images are processed after landing.

## Rationale

- useful for early hardware testing;
- tolerates limited bandwidth;
- permits lower-compute flight platforms;
- enables recorded-data development.

## Consequence

Suspicious sites discovered after landing require a new recovery mission for revisit.

# ADR-024 — Separate Structured State From File-Oriented Artifacts

## Status

Accepted.

## Decision

The database stores authoritative entities and references.

Artifact storage stores large evidence and generated files.

## Rationale

- clear durability model;
- efficient access;
- exportability;
- simpler backups;
- avoids oversized database records.

# ADR-025 — Preserve Immutable Events and Explicit Corrections

## Status

Accepted.

## Decision

Persisted events are immutable.

A correction is represented by a new event linked through causation/reference metadata.

## Rationale

- reliable audit trail;
- traceable failure analysis;
- deterministic reconstruction;
- no silent historical rewrite.

# ADR-026 — Use Versioned Model and Preprocessing Contracts

## Status

Accepted.

## Decision

Every active model must have:

- model ID;
- model version;
- artifact hash;
- input shape;
- dtype;
- preprocessing;
- class order;
- output contract;
- confidence policy;
- supported crop/class metadata.

## Rationale

Model binary identity alone is insufficient to reproduce inference.

## Consequences

- incompatible models are blocked;
- mission snapshots remain reproducible;
- optimized runtimes can be parity-tested.

# ADR-027 — Treat Dashboard State as Derived, Not Authoritative

## Status

Accepted.

## Decision

The Dashboard reconstructs its display from API-accessible authoritative mission state.

## Rationale

- dashboard restart must be safe;
- browser state cannot own flight status;
- multiple displays may exist later;
- UI bugs must not corrupt the mission.

# ADR-028 — Preserve Partial Evidence and Honest Unresolved Outcomes

## Status

Accepted.

## Decision

Failures preserve:

- raw images;
- completed predictions;
- site records;
- skip reasons;
- checkpoints;
- unresolved statuses.

The system never converts missing evidence into a healthy result.

## Rationale

- scientific honesty;
- operator trust;
- field safety;
- retry capability;
- auditability.

# ADR-029 — Use Recovery Missions Rather Than Reactivating Interrupted Flights

## Status

Accepted.

## Decision

Any physical follow-up after interruption uses a new mission linked to the source mission.

## Rationale

- conditions change;
- safety checks must be rerun;
- operator consent must be current;
- mission history remains unambiguous.

# ADR-030 — Keep Cloud and Internet Connectivity Outside the Safety Path

## Status

Accepted.

## Decision

No flight action, preflight decision, failsafe, return-home, manual takeover, or local evidence preservation depends on the internet.

## Rationale

- field connectivity is unreliable;
- safety must remain local;
- cloud outages must not affect flight.

# ADR-031 — Separate Workflow, Mission Activity, Vehicle, and Job State

## Status

Accepted.

## Decision

PlantGuard persists four independent state dimensions:

1. Mission Orchestrator owns mission workflow state.
2. Mission Orchestrator records the current mission activity.
3. Vehicle Adapter derives vehicle operational state from PX4.
4. Background Job Worker owns processing-job state.

Processing may run while the aircraft returns or lands. A job retry or checkpoint resume never changes vehicle state and never resumes physical flight.

## Rationale

- represents concurrent flight and processing honestly;
- prevents queue state from becoming mission authority;
- supports deterministic recovery and dashboard reconstruction;
- avoids contradictory single-enum definitions.

## Consequences

- events and persistence schemas carry explicit state-dimension names;
- workflow transitions, activity changes, vehicle observations, and job transitions are tested separately;
- flow diagrams may use activity aliases but may not introduce new workflow-state values.

# ADR-032 — Separate Technical Preflight, Operator Approval, and Final Takeoff Authorization

## Status

Accepted.

## Decision

Takeoff uses three ordered gates:

```text
technical preflight PASS or permitted WARNING
→ authorized operator approval linked to that snapshot
→ final takeoff authorization against current telemetry and matching versions
```

Missing approval is not a technical-preflight failure. It is a takeoff-authorization blocker. Any expired snapshot, version drift, or new safety blocker invalidates readiness and returns the workflow to preparation.

## Rationale

- removes the circular dependency between preflight and approval;
- preserves explicit human authorization;
- prevents stale approval from authorizing changed conditions;
- produces auditable safety evidence.

## Consequences

- approval records reference preflight, route, configuration, actor, and expiry data;
- the vehicle stays disarmed until final authorization succeeds;
- duplicate approval or takeoff messages remain idempotent;
- technical-preflight tests and authorization tests are separate.

## 4. Cross-Decision Constraints

The following combinations are mandatory:

```text
ADR-004 + ADR-015 + ADR-030
→ fully local core operation
```

```text
ADR-007 + ADR-018
→ layered safety and separated route authority
```

```text
ADR-005 + ADR-006 + ADR-020
→ ground-station authority with optional companion extension
```

```text
ADR-013 + ADR-014 + ADR-026
→ portable inference first, optimized inference later, same contracts
```

```text
ADR-016 + ADR-023 + ADR-029
→ processing may resume, physical flight uses a new mission
```

```text
ADR-009 + ADR-020 + ADR-031
→ workflow, vehicle, and processing authority remain separate
```

```text
ADR-007 + ADR-032
→ technical readiness, human approval, and final takeoff authorization are distinct gates
```

## 5. Decision Change Control

A decision change requires:

- change identifier;
- reason;
- affected requirements;
- affected components;
- safety impact;
- schedule impact;
- data impact;
- verification impact;
- migration plan;
- approval outcome.

Allowed outcomes:

```text
approved_for_v1
approved_as_extension
deferred
rejected
```

No implementation task may silently override an accepted ADR.

## 6. Final Decision Statement

PlantGuard UAV v1.0 deliberately prioritizes:

```text
local reliability
mature flight safety
clear ownership
traceable evidence
replaceable runtimes
ground-station simplicity
honest uncertainty
safe recovery
```

Performance and onboard deployment may evolve later, but not by weakening safety, authority, traceability, or reproducibility.
