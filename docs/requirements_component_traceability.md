# PlantGuard UAV — Requirements-to-Component Traceability

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Requirements-to-Component Traceability |
| Target release | v1.0 |
| Status | Active architecture baseline |
| Related documents | `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md`, `docs/verification_and_acceptance_plan.md`, `docs/v1_scope_baseline.md`, `docs/system_architecture.md`, `docs/component_catalog.md`, `docs/component_interfaces.md`, `docs/runtime_and_deployment_architecture.md`, `docs/mission_sequence_flows.md`, `docs/architecture_decisions.md` |
| Last updated | 2026-07-21 |

## 1. Document Purpose

This document maps every mandatory PlantGuard UAV v1.0 requirement to:

- its source;
- its primary owning component;
- supporting components;
- interface or message contract;
- runtime location;
- mission-sequence flow;
- persisted evidence;
- verification method;
- planned implementation phase;
- current status;
- unresolved dependencies.

This matrix prevents requirements from becoming orphaned between product definition and implementation.

## 2. Traceability Statuses

```text
covered_by_architecture
partially_deferred
implementation_pending
verification_pending
blocked_by_external_dependency
excluded_from_v1
```

At the end of Week 2, most included requirements are expected to be:

```text
covered_by_architecture
```

with implementation and verification still pending.

## 3. Source Documents

| Code | Source |
|---|---|
| PRD | `docs/product_requirements.md` |
| SCOPE | `docs/system_scope.md` |
| DATA | `docs/data_and_decision_contracts.md` |
| SAFETY | `docs/safety_and_failure_policy.md` |
| VERIFY | `docs/verification_and_acceptance_plan.md` |
| BASELINE | `docs/v1_scope_baseline.md` |

## 4. Farmer Workflow Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract / interface | Runtime | Sequence flow | Persisted evidence | Verification | Planned phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FW-001 | PRD | Farmer can select a saved field | Farmer Dashboard | Mission API, Persistence Layer | `SelectField`, `GetFieldDefinition` | Dashboard + backend | Flow 1 | field-selection event | UI/API integration test | W32/W48 | covered_by_architecture | saved field schema |
| FW-002 | PRD | Farmer can create a mission without terminal access | Farmer Dashboard | Mission API, Mission Orchestrator | `CreateMission` | Dashboard + backend | Flow 2 | Mission record, `MissionCreated` | end-to-end UI test | W32/W41 | covered_by_architecture | dashboard implementation |
| FW-003 | PRD | Farmer can start the workflow through one primary action path | Farmer Dashboard | Mission API, Mission Orchestrator | mission creation + preflight + approval commands | Dashboard + backend | Flows 1–7 | command/event history | farmer workflow acceptance test | W41/W50 | covered_by_architecture | final UI wording |
| FW-004 | PRD | Farmer can view mission progress | Farmer Dashboard | Mission API, Mission Orchestrator, Vehicle Adapter | `GetMissionStatus`, `MissionStateChanged`, progress events | Dashboard + backend | All active flows | mission states, progress events | UI state reconstruction test | W32/W41 | covered_by_architecture | telemetry update rate |
| FW-005 | PRD | Farmer receives map and report | Farmer Dashboard | Geospatial Mapper, Report Generator, Mission API | `GetFieldMap`, `GetReportStatus` | Dashboard + worker + backend | Flows 25–26 | GeoJSON, field map, report | end-to-end report test | W28/W41/W50 | covered_by_architecture | final report design |

## 5. Route Customization Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ROUTE-001 | PRD/SCOPE | Support automatic full-field coverage | Survey Planner | Dashboard, Safety Supervisor | `SubmitRouteIntent(automatic_coverage)`, `GenerateSurveyPlan` | Backend | Flows 3–4 | candidate route, coverage estimate | route-planner unit tests | W8 | covered_by_architecture | exact camera geometry |
| ROUTE-002 | PRD | Farmer can mark priority zones | Farmer Dashboard | Survey Planner, Geospatial Mapper | `SubmitRouteIntent` | Dashboard + backend | Flow 3 | route-intent record | UI and planner test | W8/W41 | covered_by_architecture | priority weighting |
| ROUTE-003 | PRD | Farmer can mark exclusion zones | Farmer Dashboard | Survey Planner, Safety Supervisor | `SubmitRouteIntent` | Dashboard + backend | Flows 3–4 | exclusion geometry | route/geofence test | W7/W8 | covered_by_architecture | field data |
| ROUTE-004 | PRD | Farmer may provide a custom route draft | Farmer Dashboard | Survey Planner, Safety Supervisor | expert-custom route intent | Dashboard + backend | Flows 3–4 | route draft and normalized route | malformed/unsafe route tests | W8/W41 | covered_by_architecture | expert-mode permissions |
| ROUTE-005 | DATA | Excluded areas must be reported as uninspected | Farmer Dashboard | Geospatial Mapper, Report Generator | coverage warning + skipped-area artifact | Dashboard + worker | Flows 3, 25, 26 | skipped-area GeoJSON, report warning | report coverage test | W28/W41 | covered_by_architecture | coverage metric implementation |
| ROUTE-006 | SAFETY | Farmer input cannot directly command PX4 | Survey Planner | Dashboard, Safety Supervisor, Vehicle Adapter | route intent → candidate route → approval → execution | Backend + vehicle process | Flows 3–4, 8 | approval and upload records | security/integration test | W8/W9 | covered_by_architecture | none |

## 6. Operator Authorization Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AUTH-001 | PRD/SAFETY | Operator approves every takeoff | Mission Orchestrator | Dashboard, Mission API, Safety Supervisor | `ApproveTakeoff`, `TakeoffApprovalRecorded` | Dashboard + backend | Flow 6 | operator approval record | reject takeoff without approval | W10/W12 | covered_by_architecture | auth mechanism |
| AUTH-002 | SAFETY | Approval must be current and linked to valid preflight | Safety Supervisor | Mission Orchestrator | final action validation | Backend | Flow 6 | approval + preflight references | expired preflight test | W10 | covered_by_architecture | preflight expiry policy |
| AUTH-003 | SAFETY | Unauthorized users cannot issue safety-critical commands | Mission API | Dashboard, Persistence Layer | actor/authorization context | Backend | Flows 6, 27–28 | actor ID, audit log | authorization tests | W32/W41 | covered_by_architecture | exact local auth scheme |
| AUTH-004 | SAFETY | Automatic revisit may continue under original authorization only when policy permits | Safety Supervisor | Mission Orchestrator | `ValidateRevisitPlan`, `StartRevisit` | Backend | Flows 15–16 | authorization-policy snapshot | integration test | W41–W44 | covered_by_architecture | final operator policy |

## 7. Mission-State Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| STATE-001 | PRD/BASELINE | Use canonical mission states | Mission Orchestrator | Persistence Layer, Dashboard | `MissionStateChanged` | Backend | All flows | mission-state records | state-machine tests | W4 | covered_by_architecture | none |
| STATE-002 | SAFETY | Only Mission Orchestrator changes mission state | Mission Orchestrator | all components | state-ownership rule | Backend | All flows | state transition causation | architectural test/code review | W4/W32 | covered_by_architecture | none |
| STATE-003 | DATA | State changes must be auditable | Observability and Event Logger | Mission Orchestrator, Persistence Layer | immutable events | Shared local runtime | All flows | event log | event integrity test | W30/W35 | covered_by_architecture | event-storage implementation |
| STATE-004 | SAFETY | Invalid transitions are rejected | Mission Orchestrator | Persistence Layer | transition guard | Backend | All flows | rejection record | exhaustive transition test | W4 | covered_by_architecture | none |

## 8. Flight Safety and Manual Control Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SAFE-001 | SAFETY | PX4 native failsafes remain authoritative | PX4 / Vehicle Adapter boundary | Safety Supervisor | native behavior + normalized events | Drone + vehicle process | Failure flows | PX4 logs, events | SITL failure tests | W5/W11 | covered_by_architecture | final PX4 configuration |
| SAFE-002 | SAFETY | PlantGuard Safety Supervisor owns application safety | Safety Supervisor | Mission Orchestrator, Vehicle Adapter | safety decisions | Backend | Flows 4–7, 15, failures | safety-decision records | policy unit tests | W10/W11 | covered_by_architecture | exact thresholds |
| SAFE-003 | SAFETY | Manual takeover supersedes autonomy | PX4/Vehicle Adapter | Mission Orchestrator, Safety Supervisor | `ManualTakeoverDetected` | Drone + vehicle process + backend | Flow 29 | takeover event | SITL/manual-mode test | W11/W41 | covered_by_architecture | hardware/manual controller |
| SAFE-004 | SAFETY | Dashboard failure cannot remove manual control | PX4/manual controller | Dashboard, backend | independent physical control path | Drone | Runtime failure matrix | flight-controller logs | fault-injection test | W11/W45 | covered_by_architecture | hardware |
| SAFE-005 | SAFETY | Abort normally returns/lands safely, not motor stop | Safety Supervisor | Mission Orchestrator, Vehicle Adapter | `AbortMission`, `ReturnHome`, `Land` | Backend + vehicle process | Flow 28 | abort decision/event | SITL abort tests | W11/W12 | covered_by_architecture | PX4 behavior |
| SAFE-006 | SAFETY | Geofence is never disabled to finish mission | Safety Supervisor | PX4, planners | route validation + native geofence | Backend + drone | Planning/failure flows | safety decision | geofence violation tests | W7/W10/W11 | covered_by_architecture | final geofence configuration |
| SAFE-007 | SAFETY | Safety outranks mission completion | Safety Supervisor | all components | failure/return policy | Backend | All failure flows | reason codes, mission outcome | scenario acceptance tests | W11/W48 | covered_by_architecture | none |

## 9. Preflight Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PREF-001 | SAFETY | Check vehicle connection | Safety Supervisor | Vehicle Adapter | `RunPreflight` | Backend + vehicle process | Flow 5 | check result | disconnected test | W10 | covered_by_architecture | none |
| PREF-002 | SAFETY | Check GPS and home position | Safety Supervisor | Vehicle Adapter | preflight snapshot | Backend | Flow 5 | GPS/home result | degraded GPS tests | W10 | covered_by_architecture | thresholds |
| PREF-003 | SAFETY | Check battery and reserve feasibility | Safety Supervisor | planners, Vehicle Adapter | preflight/route feasibility | Backend | Flows 5, 15 | battery decision | boundary tests | W10/W27 | covered_by_architecture | hardware battery model |
| PREF-004 | SAFETY | Check route validity | Safety Supervisor | Survey Planner | `ValidateSurveyPlan` | Backend | Flow 4 | route decision | route safety tests | W8/W10 | covered_by_architecture | exact field constraints |
| PREF-005 | SAFETY | Check camera readiness and test capture | Safety Supervisor | Camera Manager | readiness query/test capture | Backend + camera | Flow 5 | camera check | camera mock/hardware test | W10/W39 | covered_by_architecture | final camera |
| PREF-006 | SAFETY | Check storage readiness | Safety Supervisor | Mission Data Manager, Persistence Layer | readiness query | Backend | Flow 5 | storage check | failure injection | W10/W31 | covered_by_architecture | storage target |
| PREF-007 | SAFETY | Check model readiness | Safety Supervisor | Model Registry, Worker | model readiness | Backend + worker | Flow 5 | model contract snapshot | invalid model test | W10/W30 | covered_by_architecture | final models |
| PREF-008 | SAFETY | Preflight produces PASS/WARNING/BLOCKED | Safety Supervisor | Dashboard | `PreflightCompleted` | Backend | Flow 5 | preflight result | policy tests | W10 | covered_by_architecture | warning policy |
| PREF-009 | SAFETY | Preflight can expire | Safety Supervisor | Mission Orchestrator | expiry conditions | Backend | Flow 6 | timestamp/snapshot | expiry test | W10 | covered_by_architecture | expiry duration |

## 10. Survey and Capture Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SURV-001 | PRD | Perform full-field RGB survey | Survey Planner | Vehicle Adapter, Camera Manager | survey plan + `StartSurvey` | Backend + drone | Flows 8–10 | route, flight path, images | SITL/field coverage test | W8/W9/W40 | covered_by_architecture | hardware and field |
| SURV-002 | SCOPE | Use high-resolution RGB only in v1.0 | Camera Manager | Model services | capture contract | Camera + ground | Flows 9, 17 | image metadata | metadata test | W13/W39 | covered_by_architecture | final camera |
| SURV-003 | DATA | Every image is linked to mission, route, waypoint, and telemetry | Mission Data Manager | Camera Manager, Vehicle Adapter | `ImageCaptured` | Backend + camera | Flows 9, 17 | image record/manifests | traceability test | W13 | covered_by_architecture | clock/telemetry synchronization |
| SURV-004 | DATA | Raw images retained by default | Mission Data Manager | Artifact Storage | retention policy | Ground storage | Capture flows | raw image files | retention test | W13/W31 | covered_by_architecture | duration policy |
| SURV-005 | VERIFY | Coverage is measurable | Geospatial Mapper | Survey Planner, Vehicle Adapter | coverage artifacts | Worker | Flows 25–26 | coverage GeoJSON/metrics | field coverage calculation | W28/W48 | covered_by_architecture | geospatial accuracy |
| SURV-006 | SAFETY | Complete camera failure triggers return | Safety Supervisor | Camera Manager, Mission Orchestrator | camera failure event | Backend | Flow 33 | failure and return events | injected failure test | W11/W39 | covered_by_architecture | final camera behavior |

## 11. Image-Quality Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QUAL-001 | DATA | Validate blur, exposure, corruption, obstruction, visibility, metadata | Image Quality Validator | Mission Data Manager | `ValidateImage` | Worker | Flows 11, 19 | quality results/manifests | fixture-based tests | W14 | covered_by_architecture | threshold calibration |
| QUAL-002 | DATA | Rejected images do not enter normal inference | Image Quality Validator | Worker, model services | `ImageRejected` | Worker | Flows 11, 19 | eligibility flag | integration test | W14/W29 | covered_by_architecture | none |
| QUAL-003 | SAFETY | Persistent quality failure cannot be treated as healthy coverage | Mission Orchestrator | Safety Supervisor, Report Generator | quality failure policy | Backend + worker | Flow 34 | rejected-image ratio, warning | scenario test | W14/W41 | covered_by_architecture | rejection threshold |
| QUAL-004 | DATA | Rejection reasons are explicit | Image Quality Validator | Dashboard, Report Generator | reason codes | Worker | Flows 11, 19 | rejected manifest | reason-code tests | W14 | covered_by_architecture | thresholds |

## 12. Health Screening Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SCREEN-001 | PRD/DATA | Screen survey observations as healthy, unhealthy, or uncertain | Aerial Health Screening Service | Image Quality Validator, Model Registry | `ScreenSurveyImages` | Worker | Flow 12 | observations/predictions | model evaluation + contract tests | W18–W20 | covered_by_architecture | aerial dataset/model |
| SCREEN-002 | DATA | High-confidence unhealthy creates/supports suspicious site | Suspicious-Site Clusterer | Screening Service | observation contract | Worker | Flows 12–13 | observation membership | integration test | W26 | covered_by_architecture | thresholds |
| SCREEN-003 | DATA | Uncertain creates/supports suspicious site | Suspicious-Site Clusterer | Screening Service | observation contract | Worker | Flows 12–13 | observation/site record | integration test | W26 | covered_by_architecture | uncertainty threshold |
| SCREEN-004 | DATA | Healthy observation alone does not cause revisit | Mission Orchestrator | Screening Service | screening result handling | Backend + worker | Flows 12–14 | absence of target | scenario test | W29 | covered_by_architecture | threshold calibration |
| SCREEN-005 | SAFETY | Screening failure disables automatic AI revisit planning | Mission Orchestrator | Worker, Safety Supervisor | screening failure event | Backend | Flow 35 | failure and state event | injected failure test | W11/W29 | covered_by_architecture | none |

## 13. Suspicious-Site Clustering Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SITE-001 | PRD | Group related observations into suspicious sites | Suspicious-Site Clusterer | Geospatial Mapper | `ClusterSuspiciousObservations` | Worker | Flow 13 | site records | clustering tests | W26 | covered_by_architecture | spatial thresholds |
| SITE-002 | DATA | Suppress duplicates | Suspicious-Site Clusterer | Persistence Layer | site update contract | Worker | Flow 13 | membership records | duplicate fixture test | W26 | covered_by_architecture | overlap/distance policy |
| SITE-003 | DATA | Preserve supporting observations | Suspicious-Site Clusterer | Mission Data Manager | site membership | Worker | Flow 13 | observation IDs | traceability test | W26 | covered_by_architecture | none |
| SITE-004 | VERIFY | Measure duplicate-site rate and location error | Geospatial Mapper | Site Clusterer | evaluation artifacts | Worker | W48 evaluation flow | metrics files | field evaluation | W48 | covered_by_architecture | ground truth |

## 14. Revisit Planning and Execution Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REV-001 | PRD | Always attempt revisit for unhealthy/uncertain sites when safe | Mission Orchestrator | Revisit Planner, Safety Supervisor | `GenerateRevisitPlan`, `ValidateRevisitPlan` | Backend | Flows 14–15 | targets/skip reasons | scenario tests | W27/W41 | covered_by_architecture | battery/route policy |
| REV-002 | SAFETY | Revisit plus return plus landing plus reserve must be feasible | Safety Supervisor | Revisit Planner, Vehicle Adapter | revisit safety decision | Backend | Flow 15 | feasibility record | energy-boundary tests | W27/W41 | covered_by_architecture | hardware energy model |
| REV-003 | SAFETY | Safe priority subset is allowed | Revisit Planner | Safety Supervisor | approved safe subset | Backend | Flow 15 | approved subset | subset selection test | W27 | covered_by_architecture | priority scoring |
| REV-004 | DATA | Skipped revisit reason is preserved | Safety Supervisor | Report Generator | skip reason codes | Backend | Flows 15, 26 | skip record | report test | W27/W41 | covered_by_architecture | none |
| REV-005 | PRD | Capture multiple revisit images | Camera Manager | Mission Data Manager | repeated `CaptureImage` | Camera + ground | Flow 17 | revisit image manifest | capture policy test | W42 | covered_by_architecture | final camera/gimbal |
| REV-006 | SAFETY | Same-flight revisit may proceed without second approval only under policy | Safety Supervisor | Mission Orchestrator | authorization policy | Backend | Flows 15–16 | policy snapshot | acceptance test | W41 | covered_by_architecture | final operator policy |

## 15. Revisit Health and Disease Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CLASS-001 | DATA | Reassess revisit image as healthy/unhealthy/uncertain | Revisit Health Reassessment Service | Image Quality Validator, Model Registry | `ReassessRevisitHealth` | Worker | Flow 20 | per-image evidence | model eval + contract test | W21/W24/W43 | covered_by_architecture | adapted model |
| CLASS-002 | DATA | Disease classification runs only on eligible unhealthy evidence | PlantGuard Disease Classifier | Reassessment Service | `ClassifyDisease` preconditions | Worker | Flow 21 | health reference + prediction | integration test | W21/W24 | covered_by_architecture | model support |
| CLASS-003 | DATA | Classifier may withhold prediction | PlantGuard Disease Classifier | Result Aggregator | structured unsupported/uncertain result | Worker | Flow 21 | reason codes | threshold tests | W22/W24 | covered_by_architecture | calibration |
| CLASS-004 | DATA | Preserve top-k alternatives where useful | PlantGuard Disease Classifier | Dashboard, Report Generator | disease evidence contract | Worker | Flow 21 | top-k records | output contract test | W21/W24 | covered_by_architecture | UI policy |
| CLASS-005 | SAFETY/DATA | Classifier failure does not discard unhealthy evidence | Mission Orchestrator | Disease Classifier, Aggregator | failure event | Backend + worker | Flow 36 | health evidence + failure | injected failure test | W29/W43 | covered_by_architecture | none |

## 16. Multi-Image Aggregation and Final Result Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AGG-001 | DATA | Reject unusable revisit views before aggregation | Multi-Image Result Aggregator | Image Quality Validator | aggregation input contract | Worker | Flow 22 | selected evidence set | unit tests | W24 | covered_by_architecture | quality policy |
| AGG-002 | DATA | Weight evidence by quality | Multi-Image Result Aggregator | Image Quality Validator | aggregation policy | Worker | Flow 22 | quality weights | unit tests | W24 | covered_by_architecture | weighting scheme |
| AGG-003 | DATA | Require sufficient agreement | Multi-Image Result Aggregator | model services | agreement metrics | Worker | Flow 22 | agreement score | conflict tests | W24 | covered_by_architecture | agreement threshold |
| AGG-004 | DATA | Produce `healthy_after_suspicious_survey` when revisit confirms healthy | Multi-Image Result Aggregator | Reassessment Service | final result contract | Worker | Flow 22 | final result | scenario test | W24/W43 | covered_by_architecture | thresholds |
| AGG-005 | DATA | Produce disease-identified status only when evidence is sufficient | Multi-Image Result Aggregator | Disease Classifier | final result contract | Worker | Flow 22 | final result | scenario test | W24 | covered_by_architecture | confidence threshold |
| AGG-006 | DATA | Preserve uncertainty/manual inspection | Multi-Image Result Aggregator | Report Generator | final status + reason | Worker | Flow 22 | final result/reason | scenario tests | W24/W41 | covered_by_architecture | policy thresholds |
| AGG-007 | DATA | Revisit failure produces visible unresolved result | Multi-Image Result Aggregator | Mission Orchestrator | `revisit_not_completed` | Worker + backend | Flow 22 | final site result | report test | W41/W44 | covered_by_architecture | none |

## 17. Geospatial Mapping Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GEO-001 | PRD | Produce field-health map | Geospatial Mapper | Report Generator, Dashboard | `GenerateFieldMap` | Worker | Flow 25 | `field_map.html`, GeoJSON | map-generation test | W28 | covered_by_architecture | mapping library |
| GEO-002 | DATA | Link observations to geographic context | Geospatial Mapper | Camera Manager, Vehicle Adapter | image/telemetry contracts | Worker | Capture + Flow 25 | observation GeoJSON | coordinate test | W25 | covered_by_architecture | camera/GPS model |
| GEO-003 | DATA | Export boundary, route, observations, sites, revisits, final results | Geospatial Mapper | Mission Data Manager | GeoJSON artifacts | Worker | Flow 25 | GeoJSON files | schema validation | W28 | covered_by_architecture | none |
| GEO-004 | VERIFY | Measure suspicious-site position error | Geospatial Mapper | Site Clusterer | evaluation metrics | Worker | field evaluation | error report | ground-truth test | W48 | covered_by_architecture | survey ground truth |
| GEO-005 | DATA | Identify surveyed versus skipped region | Geospatial Mapper | Survey Planner | coverage geometry | Worker | Flows 3, 25 | coverage/skipped GeoJSON | geometry tests | W28 | covered_by_architecture | route/camera footprint |

## 18. Reporting Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REP-001 | PRD | Generate farmer-facing report | Report Generator | Dashboard, Geospatial Mapper | `GenerateReport` | Worker | Flow 26 | `report.html` | end-to-end test | W41/W50 | covered_by_architecture | final UI content |
| REP-002 | DATA | Include evidence images and confidence/uncertainty | Report Generator | Aggregator, Mission Data Manager | report input contract | Worker | Flow 26 | report sections | snapshot test | W41 | covered_by_architecture | presentation design |
| REP-003 | DATA | Report unresolved and skipped sites | Report Generator | Safety Supervisor, Aggregator | result/skip contracts | Worker | Flow 26 | report entries | scenario test | W41 | covered_by_architecture | none |
| REP-004 | DATA | Healthy/unhealthy percentages refer only to observed regions unless counting is proven | Report Generator | Geospatial Mapper | coverage-aware summary | Worker | Flow 26 | mission summary | calculation test | W41/W48 | covered_by_architecture | plant-counting status |
| REP-005 | DATA | No treatment recommendations | Report Generator | Dashboard | content policy | Worker | Flow 26 | report content | content test | W41 | covered_by_architecture | none |

## 19. Local and Offline Operation Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OFF-001 | SCOPE | Core system works without internet | Runtime Architecture | all components | local-only deployment | Ground station + drone | All flows | deployment config | offline end-to-end test | W36/W45 | covered_by_architecture | hardware networking |
| OFF-002 | BASELINE | No cloud synchronization | Mission Data Manager | Persistence Layer | local artifact/storage contracts | Ground station | All data flows | local paths | network-disconnected test | W31/W36 | covered_by_architecture | none |
| OFF-003 | SAFETY | Safety does not depend on dashboard or AI | PX4/Safety Supervisor | Vehicle Adapter | independent failure paths | Drone + backend | failure flows | safety events | fault-injection test | W11/W45 | covered_by_architecture | hardware |
| OFF-004 | SCOPE | Optional companion sync is local-only | Mission Data Manager | companion runtime | buffered-event contracts | Companion + ground | runtime reconciliation | buffer logs | disconnect/reconnect test | extension | partially_deferred | companion hardware |

## 20. Persistence and Traceability Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TRACE-001 | DATA | Every result links to mission, field, site, images, model, config, timestamp | Mission Data Manager | all producers, Persistence Layer | canonical identifiers | Backend + worker | All data flows | DB references/manifests | traceability audit | W13/W30 | covered_by_architecture | schema design |
| TRACE-002 | DATA | Raw and structured artifacts use frozen mission layout | Mission Data Manager | Artifact Storage | artifact layout | Ground storage | capture/analysis/report | mission directory | layout test | W13/W31 | covered_by_architecture | none |
| TRACE-003 | DATA | Preserve model and software versions | Model Registry | Mission Data Manager | metadata snapshots | Backend + worker | mission creation/inference | metadata files | reproducibility test | W30 | covered_by_architecture | Git integration |
| TRACE-004 | SAFETY | Partial data is preserved | Mission Data Manager | Worker, Persistence Layer | checkpoint/artifact contracts | Ground station | failure flows | partial manifests | fault-injection test | W31/W45 | covered_by_architecture | atomic writes |
| TRACE-005 | DATA | Events are append-only | Observability and Event Logger | Persistence Layer | event envelope | Shared runtime | All flows | event log | immutability test | W30/W35 | covered_by_architecture | event-store design |

## 21. Resumability and Recovery Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REC-001 | SAFETY | Processing may resume from checkpoints | Background Job Worker | Mission Orchestrator | `ResumeJob` | Worker | Flow 42 | checkpoint/job record | crash-resume test | W31/W33 | covered_by_architecture | queue implementation |
| REC-002 | SAFETY | Physical flight never auto-resumes | Mission Orchestrator | Safety Supervisor, Vehicle Adapter | restart reconciliation | Backend | Flow 43 | reconciliation event | restart test | W11/W45 | covered_by_architecture | none |
| REC-003 | SAFETY | Recovery flight uses a new mission | Mission Orchestrator | Dashboard, Safety Supervisor | `CreateRecoveryMission` | Dashboard + backend | Flow 44 | source relationship | integration test | W41/W45 | covered_by_architecture | UI |
| REC-004 | DATA | Existing valid evidence is reused in recovery | Mission Data Manager | Persistence Layer | source references | Backend | Flow 44 | evidence links | traceability test | W31/W45 | covered_by_architecture | schema |

## 22. Model Metadata Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MODEL-001 | DATA | Store model ID/version/artifact | Model Registry | Mission Data Manager | model contract | Backend | mission creation/inference | model metadata | contract tests | W30 | covered_by_architecture | final model files |
| MODEL-002 | DATA | Store preprocessing and class order | Model Registry | model services | preprocessing contract | Backend + worker | inference flows | metadata snapshot | parity test | W20/W24/W30 | covered_by_architecture | export pipeline |
| MODEL-003 | DATA | Block incompatible model | Model Registry | Safety Supervisor | readiness result | Backend | Flow 5 | blocker | invalid-contract test | W30 | covered_by_architecture | none |
| MODEL-004 | DATA | Record confidence policy | Model Registry | Aggregator | configuration reference | Backend + worker | inference/aggregation | policy snapshot | reproducibility test | W20/W24/W30 | covered_by_architecture | calibrated thresholds |
| MODEL-005 | SCOPE | ONNX Runtime is portable baseline | Model Registry | model services | runtime adapter | Worker | inference flows | runtime metadata | parity/benchmark | W20/W24/W30 | covered_by_architecture | exported models |
| MODEL-006 | SCOPE | TensorRT/C++ remain optional extensions | Model Registry | optimized workers | same interface contracts | Worker/companion | extension flows | parity results | optimization tests | extension | covered_by_architecture | hardware |

## 23. Observability Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OBS-001 | DATA | Record mission events and failures | Observability and Event Logger | all components | event envelope | All local processes | All flows | JSONL/event records | log completeness test | W30/W35 | covered_by_architecture | log implementation |
| OBS-002 | VERIFY | Record latency and resource use | Observability and Event Logger | Worker, model runtimes | metrics contract | Worker/backend | processing flows | metrics files | benchmark test | W35/W49 | covered_by_architecture | metrics tooling |
| OBS-003 | DATA | Correlate messages and jobs | Observability and Event Logger | all components | correlation/causation IDs | All local processes | All flows | trace chain | correlation test | W30/W35 | covered_by_architecture | none |
| OBS-004 | SAFETY | Required audit loss degrades readiness | Safety Supervisor | Observability | readiness check | Backend | preflight/failures | blocker/warning | failure-injection test | W10/W35 | covered_by_architecture | audit threshold |

## 24. Performance and Deployment Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Contract | Runtime | Flow | Evidence | Verification | Phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PERF-001 | VERIFY | Long-running work must not block API | Background Job Worker | Mission API | job contract | Backend + worker | processing flows | API/job timings | load test | W33/W35 | covered_by_architecture | queue |
| PERF-002 | VERIFY | Measure model latency | Observability | model services | inference timing | Worker | inference flows | benchmark metrics | benchmark report | W49 | covered_by_architecture | hardware |
| PERF-003 | SCOPE | Ground-station inference is acceptable for v1.0 | Runtime Architecture | Worker | deployment profile | Ground station | normal mission | deployment record | field test | W40–W44 | covered_by_architecture | bandwidth/latency |
| PERF-004 | SCOPE | Companion/TensorRT/C++ optimizations are non-blocking | Model Registry | worker/runtime adapters | compatible interfaces | optional runtime | extension | parity/benchmark | extension benchmark | extension | covered_by_architecture | hardware |
| PERF-005 | VERIFY | System supports bounded resource use | Background Job Worker | Observability | resource classes/concurrency | Worker | job flows | metrics | stress test | W33/W49 | covered_by_architecture | final hardware |

## 25. Release-Gate Requirements

| ID | Source | Requirement | Primary owner | Supporting components | Evidence | Verification | Planned phase | Status | Dependency |
|---|---|---|---|---|---|---|---|---|
| REL-001 | VERIFY | At least 5 successful real end-to-end missions | Verification process | all components | field-test results | campaign review | W45–W48 | covered_by_architecture | hardware/field access |
| REL-002 | VERIFY | At least 3 missions on different days/conditions | Verification process | Observability | mission metadata | field-test review | W45–W48 | covered_by_architecture | field access |
| REL-003 | VERIFY | 100% safe return or controlled landing in evaluated missions | Safety Supervisor/PX4 | Vehicle Adapter | flight logs | field-test review | W45–W48 | covered_by_architecture | hardware |
| REL-004 | VERIFY | Zero unrecovered safety-critical failures | Safety Supervisor | Observability | failure records | release audit | W48/W52 | covered_by_architecture | test campaign |
| REL-005 | VERIFY | Farmer workflow without terminal | Farmer Dashboard | Mission API | usability evidence | user acceptance test | W50 | covered_by_architecture | final UI |
| REL-006 | VERIFY | No silent data loss | Mission Data Manager | Persistence Layer | manifests/checkpoints | failure test | W31/W45 | covered_by_architecture | implementation |
| REL-007 | VERIFY | Field-separated model thresholds met | Model evaluation process | model services | evaluation reports | model-gate review | W20/W24/W48 | covered_by_architecture | data |
| REL-008 | VERIFY | Geospatial targets validated | Geospatial Mapper | verification tooling | location-error report | ground-truth review | W48 | covered_by_architecture | ground truth |

## 26. Metric Traceability

| Metric | Primary owner | Evidence | Verification phase |
|---|---|---|---|
| Usable field coverage | Geospatial Mapper | coverage GeoJSON and summary | W48 |
| Capture success | Camera Manager | capture events/manifests | W40/W48 |
| Accepted image rate | Image Quality Validator | accepted/rejected manifests | W14/W48 |
| Metadata completeness | Mission Data Manager | manifest audit | W13/W48 |
| Unhealthy recall | Aerial Health Screening Service | field-separated evaluation | W20/W48 |
| Screening macro F1 | Screening Service | evaluation report | W20 |
| Disease macro F1 | PlantGuard Disease Classifier | evaluation report | W24/W48 |
| Top-3 disease accuracy | Disease Classifier | evaluation report | W24 |
| High-confidence disease precision | Disease Classifier/Aggregator | calibration report | W24/W48 |
| Correct withholding | Aggregator | uncertainty evaluation | W24/W48 |
| Revisit reach | Vehicle Adapter/Revisit Planner | revisit execution records | W44/W48 |
| Usable revisit capture | Camera Manager/Quality Validator | revisit manifests | W44/W48 |
| Site resolution | Aggregator | final site results | W44/W48 |
| Site position error | Geospatial Mapper | ground-truth comparison | W48 |
| Duplicate-site rate | Site Clusterer | clustering evaluation | W26/W48 |

## 27. v1.0 Exclusions Traceability

| ID | Source | Excluded capability | Enforcement owner | Verification |
|---|---|---|---|---|
| EX-001 | BASELINE | Custom frame/motors/ESC/flight controller | Scope baseline | hardware review |
| EX-002 | BASELINE | Spraying | Product requirements | feature audit |
| EX-003 | BASELINE | Drone swarms | Scope baseline | architecture audit |
| EX-004 | BASELINE | Multispectral imaging | Camera Manager/model scope | hardware/model audit |
| EX-005 | BASELINE | Obstacle-avoidance research | Safety/scope baseline | route/scope review |
| EX-006 | BASELINE | All 132 diseases from high altitude | Screening/classification separation | model-card review |
| EX-007 | BASELINE | Treatment recommendations | Report Generator | content test |
| EX-008 | BASELINE | Cloud synchronization | Runtime architecture | offline/network test |
| EX-009 | BASELINE | Mandatory mobile-native application | Dashboard scope | release audit |
| EX-010 | BASELINE | Automatic physical-flight resume | Mission Orchestrator | restart test |

## 28. Unresolved Dependencies

The following remain explicit and do not invalidate architecture coverage:

| Dependency | Affected requirements | Resolution source |
|---|---|---|
| Final drone model | safety, battery, payload, weather | manufacturer docs and hardware tests |
| Final camera/gimbal | capture, image quality, geolocation | hardware evaluation |
| Weather rating | precipitation policy | manufacturer documentation |
| Applicable legal limits | altitude, VLOS, operation | current regulation review |
| Battery thresholds | preflight and revisit feasibility | flight testing |
| Image-quality thresholds | acceptance and adaptation | validation data |
| Model confidence thresholds | screening/classification/aggregation | calibration |
| Companion hardware | optional onboard mode | performance testing |
| Exact database | persistence implementation | Week 3/31 design |
| Exact queue | job execution | Week 3/33 design |
| Authentication mechanism | command authorization | API/security design |
| Geospatial error target implementation | location accuracy | field calibration |
| First validation crop | datasets and field tests | access and ground truth |

## 29. Orphan-Requirement Audit

A requirement is orphaned if it lacks any of:

- primary owner;
- supporting interface;
- persisted evidence;
- verification path;
- planned phase.

At the end of Week 2 Day 6:

```text
mandatory requirements without a primary owner: 0
mandatory requirements without an interface path: 0
mandatory requirements without persisted evidence: 0
mandatory requirements without a verification path: 0
```

Implementation and field verification remain pending.

## 30. Change-Control Rule

When a Week 1 requirement changes:

1. update its source document;
2. update this traceability row;
3. identify affected ADRs;
4. identify affected components;
5. update interfaces;
6. update sequence flows;
7. update verification;
8. record scope-change outcome.

No developer should resolve a product-level contradiction only in source code.

## 31. Day 6 Acceptance Criteria

Day 6 is complete when:

- every mandatory requirement has a primary owner;
- every requirement has supporting components;
- every requirement has an interface or contract;
- runtime location is known;
- sequence flow is identified;
- persisted evidence is identified;
- verification is defined;
- planned phase is identified;
- exclusions are explicit;
- unresolved dependencies remain visible;
- no mandatory requirement is orphaned;
- the matrix is ready for Day 7 architecture audit and freeze.

## 32. Final Traceability Statement

PlantGuard UAV v1.0 maintains a continuous chain:

```text
product requirement
→ architecture decision
→ owning component
→ interface contract
→ runtime location
→ mission sequence
→ persisted evidence
→ verification method
```

This chain ensures that implementation, testing, field evaluation, and release decisions remain connected to the frozen product and safety baseline.
