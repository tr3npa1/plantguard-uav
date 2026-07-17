# PlantGuard UAV — v1.0 Scope Baseline

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | v1.0 Scope Baseline |
| Target release | v1.0 |
| Status | Frozen baseline |
| Scope baseline version | 1.0 |
| Related documents | `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md`, `docs/verification_and_acceptance_plan.md` |
| Last updated | 2026-07-16 |

## 1. Document Purpose

This document freezes the PlantGuard UAV v1.0 scope established during Week 1.

It serves as:

- the authoritative index for all Week 1 requirements;
- the document-precedence guide;
- the canonical terminology reference;
- the summary of frozen product decisions;
- the list of deliberately unresolved values;
- the scope-change control policy;
- the consistency certificate used before Week 2 architecture design.

This document does not replace the detailed Week 1 specifications. It defines how those documents fit together and prevents later implementation from silently changing the agreed product.

## 2. Scope Baseline Status

The PlantGuard UAV v1.0 scope is considered frozen when this document is accepted.

After scope freeze:

- implementation may refine internal design;
- configuration values may be calibrated;
- hardware-dependent values may be resolved;
- requirements may be clarified without changing intent;
- major features may not be added or removed without formal scope-change review.

The frozen baseline applies to:

```text
product behavior
operating environment
data contracts
decision logic
safety behavior
verification requirements
release gates
portfolio extensions
explicit exclusions
```

## 3. Authoritative Document Map

Each topic has one primary authoritative document.

| Topic | Authoritative document |
|---|---|
| Farmer experience, product behavior, functional requirements, dashboard expectations | `docs/product_requirements.md` |
| Operating environment, crop assumptions, sensor assumptions, field assumptions, flight assumptions, weather modes | `docs/system_scope.md` |
| Data entities, inputs, outputs, status values, screening/revisit logic, confidence policy, result contracts | `docs/data_and_decision_contracts.md` |
| Preflight, blockers, warnings, abort, return-to-home, failures, partial data, recovery | `docs/safety_and_failure_policy.md` |
| Metrics, verification methods, release thresholds, release gates, definition of done | `docs/verification_and_acceptance_plan.md` |
| Document precedence, canonical terminology, scope freeze, unresolved values, change control | `docs/v1_scope_baseline.md` |

## 3.1 Precedence Rule

When two documents appear to overlap:

1. use the document assigned to that topic above;
2. interpret overlapping text consistently with the frozen end-to-end workflow;
3. never use an older general statement to override a newer topic-specific contract;
4. record and resolve any real contradiction before implementation continues.

## 3.2 Safety Precedence

Safety behavior always takes precedence over:

- route completion;
- field coverage;
- model inference;
- revisit completion;
- latency targets;
- disease classification;
- portfolio-extension goals.

The safety policy and native flight-controller failsafes remain authoritative during conflict.

## 4. Frozen Product Statement

PlantGuard UAV v1.0 is an operator-authorized autonomous RGB field-inspection system for one predefined agricultural field at a time using one programmable drone.

The system:

1. loads a saved field;
2. performs preflight checks;
3. requires operator approval before takeoff;
4. surveys the complete field;
5. captures geotagged RGB imagery;
6. screens observations as healthy, unhealthy, or uncertain;
7. groups unhealthy and uncertain observations into suspicious sites;
8. generates a safe lower-altitude revisit plan;
9. revisits eligible suspicious sites;
10. reassesses health;
11. identifies a likely disease where evidence is sufficient;
12. preserves uncertainty where evidence is insufficient;
13. returns home and lands;
14. produces a field-health map and farmer-facing report.

The system supports inspection and prioritization. It does not provide definitive agronomic diagnosis or treatment recommendations.

## 5. Frozen End-to-End Workflow

The canonical v1.0 workflow is:

```text
select saved field
→ load field and mission configuration
→ connect one drone
→ run preflight
→ show readiness and blockers
→ obtain operator takeoff approval
→ take off
→ survey complete field
→ capture geotagged RGB imagery
→ validate image quality
→ screen healthy / unhealthy / uncertain
→ group suspicious observations into sites
→ validate battery, route, weather, and vehicle health
→ generate revisit mission
→ revisit eligible suspicious sites
→ capture higher-detail images
→ reassess health
→ classify disease where supported
→ preserve uncertain/manual-inspection outcomes
→ return home
→ land
→ generate map, metrics, evidence, and report
```

No implementation may silently replace this with:

- high-altitude direct disease diagnosis;
- survey-only behavior presented as full v1.0;
- treatment recommendation;
- autonomous spraying;
- takeoff without operator approval;
- revisit without safety validation.

## 6. Canonical User

The primary user is:

```text
farmer
```

The operator may be the farmer or another authorized person responsible for flight supervision.

The farmer shall not need to understand or directly operate:

```text
PX4 internals
ROS 2 internals
MAVSDK internals
ONNX Runtime internals
model thresholds
GeoJSON internals
database internals
terminal commands
manual waypoint coordinates
```

## 7. Canonical Mission Scope

PlantGuard UAV v1.0 supports:

```text
one active field
one connected drone
one active mission
one saved field boundary
one operator-authorized takeoff
```

The system does not support:

```text
multiple simultaneous drones
multiple simultaneous field missions
swarm behavior
```

## 8. Canonical Terminology

The following terms are authoritative.

### 8.1 Field and Flight Terms

```text
field
field boundary
home location
takeoff area
exclusion zone
geofence
survey route
revisit route
survey waypoint
revisit waypoint
```

### 8.2 Image and Perception Terms

```text
survey image
survey observation
healthy observation
unhealthy observation
uncertain observation
suspicious site
revisit target
revisit image
final site result
```

### 8.3 Result Terms

```text
healthy
healthy_after_suspicious_survey
unhealthy_disease_identified
unhealthy_disease_uncertain
health_status_unresolved
manual_inspection_recommended
revisit_not_completed
```

### 8.4 Operational Terms

```text
preflight
operator approval
manual takeover
pause
abort
return-to-home
controlled landing
recovery mission
partial mission
```

### 8.5 Terms to Avoid in Technical Contracts

Avoid vague terms such as:

```text
bad plant
disease point
infected spot
AI target
problem zone
broken crop
```

Farmer-facing language may use simpler explanations, but internal contracts shall use canonical terminology.

## 9. Canonical Mission States

The canonical mission states are:

```text
IDLE
PREFLIGHT
AWAITING_OPERATOR_APPROVAL
TAKEOFF
SURVEY
INITIAL_ANALYSIS
REVISIT_PLANNING
REVISIT
FINAL_CLASSIFICATION
RETURN_TO_HOME
LANDING
REPORT_GENERATION
COMPLETE
ABORTED
FAILED
```

The canonical serialized values are:

```text
idle
preflight
awaiting_operator_approval
takeoff
survey
initial_analysis
revisit_planning
revisit
final_classification
return_to_home
landing
report_generation
complete
aborted
failed
```

These states form the basis of the Week 4 mission-state implementation.

## 10. Canonical Survey Decision Logic

### 10.1 High-Confidence Healthy

```text
record as healthy
→ do not create a suspicious site from that observation
→ no revisit required solely from that observation
```

### 10.2 High-Confidence Unhealthy

```text
create or support suspicious site
→ mark revisit required
→ always attempt revisit
→ identify disease using higher-detail imagery
```

### 10.3 Uncertain Survey Result

```text
preserve observation
→ create or support suspicious site
→ always attempt revisit
→ reassess health and disease
```

An uncertain survey result shall never be silently converted to healthy.

### 10.4 Meaning of “Always Attempt Revisit”

“Always attempt revisit” means:

- include the site in revisit planning;
- validate route and geofence;
- validate weather and visibility;
- validate vehicle and camera health;
- validate battery reserve;
- honor operator commands.

A site may remain unrevisited when any safety or mission constraint makes revisit unsafe or impossible.

## 11. Canonical Post-Revisit Decision Logic

### 11.1 Unhealthy Confirmed and Disease Identified

```text
unhealthy high confidence
+
disease high confidence
→ return disease and confidence
```

Final status:

```text
unhealthy_disease_identified
```

### 11.2 Unhealthy Confirmed but Disease Uncertain

```text
unhealthy high confidence
+
disease low confidence or inconsistent
→ return unhealthy
→ withhold disease label
→ recommend manual inspection
```

Final status:

```text
unhealthy_disease_uncertain
```

### 11.3 Healthy Confirmed After Suspicious Survey

```text
healthy high confidence
→ return healthy
→ retain caution that the survey appeared abnormal
→ suggest optional manual inspection
```

Final status:

```text
healthy_after_suspicious_survey
```

The site remains visible on the final map.

### 11.4 Health Remains Uncertain

```text
do not force healthy or unhealthy
→ recommend manual inspection
```

Final status:

```text
health_status_unresolved
```

### 11.5 Revisit Not Completed

```text
preserve site
→ preserve reason
→ recommend manual inspection
```

Final status:

```text
revisit_not_completed
```

## 12. Canonical Confidence Policy

Exact thresholds are not frozen in Week 1.

Thresholds shall be:

- model-specific;
- calibrated using validation data;
- stored in versioned configuration;
- included in mission metadata;
- separate from dashboard code;
- traceable in final results.

The system shall support:

```text
healthy threshold
unhealthy threshold
uncertain interval
minimum disease confidence
minimum top-1 versus top-2 margin
minimum image-quality score
minimum multi-view agreement
```

No model shall be rewarded for forcing unsupported predictions.

## 13. Canonical Safety Rules

The following rules are frozen.

1. Every takeoff requires operator approval.
2. Hard blockers cannot be overridden through the dashboard.
3. Manual takeover immediately supersedes autonomy.
4. Abort cancels remaining autonomous work and normally returns home.
5. Return Home cancels remaining survey and revisit work.
6. Native flight-controller failsafes remain enabled.
7. PlantGuard shall not disable geofence or safety systems to finish a mission.
8. Revisit begins only when revisit, return, landing, and reserve are feasible.
9. Partial mission data is always preserved.
10. AI or backend failure must not destabilize the aircraft.
11. Physical flight never automatically resumes after interruption.
12. A recovery flight requires a new mission, full preflight, and new approval.
13. Critical battery handling remains owned by the flight controller.
14. Persistent unsafe weather or image-quality degradation triggers return or safe termination.
15. Safe aircraft recovery has priority over every product objective.

## 14. Canonical Preflight Result Values

```text
PASS
WARNING
BLOCKED
```

### 14.1 PASS

All required conditions are satisfied.

### 14.2 WARNING

The condition is visible to the operator and flight may proceed only when no hard blocker exists.

### 14.3 BLOCKED

The aircraft remains disarmed.

Hard blockers include:

```text
operator approval missing
manual takeover unavailable
return-to-home unavailable
critical flight-controller fault
invalid position
invalid home position
insufficient battery
invalid field boundary
unsafe route
required geofence unavailable
unknown obstacle risk
camera unavailable
storage unavailable
required model unavailable in normal mode
unsupported weather
required VLOS unavailable
operator judges conditions unsafe
```

## 15. Canonical Weather Modes

The supported weather modes are:

```text
nominal
degraded_visibility
light_precipitation
```

### 15.1 Nominal Mode

```text
dry daylight
adequate visibility
supported wind
standard altitude
standard speed
standard overlap
standard reserve
```

### 15.2 Degraded-Visibility Mode

May be used for light mist or light fog only when:

- required visual line of sight remains available;
- obstacle clearance remains reliable;
- image-quality checks pass;
- selected hardware permits operation;
- safe return remains possible.

Possible adaptations:

```text
lower altitude
lower speed
higher overlap
shorter route legs
more frequent image checks
larger battery reserve
fewer revisit targets
```

### 15.3 Light-Precipitation Mode

May be used only when the entire selected platform is explicitly approved for the encountered precipitation.

The complete platform includes:

```text
aircraft
camera
gimbal
companion computer
payload enclosure
connectors
power electronics
storage system
```

Lowering altitude does not make non-weather-rated hardware safe.

## 16. Canonical Data-Retention Policy

Raw mission images are retained by default for:

- debugging;
- reprocessing;
- ground-truth review;
- failure analysis;
- model improvement;
- research evidence;
- reproducibility.

The operator may delete mission images after review.

Derived artifacts remain unless explicitly deleted:

```text
mission metadata
predictions
site records
maps
reports
logs
configuration snapshots
model metadata
```

## 17. Canonical Traceability Rule

Every final result shall be traceable to:

```text
field
mission
survey image
survey observation
suspicious site
revisit image
model
model version
configuration
timestamp
```

A final disease result without evidence or model metadata is invalid.

## 18. Mandatory v1.0 Features

The following features are mandatory for the core PlantGuard UAV v1.0 release:

```text
saved field selection
one drone and one field at a time
operator-approved takeoff
preflight validation
full-field survey
geotagged RGB image capture
image-quality validation
healthy / unhealthy / uncertain screening
suspicious-site grouping
automatic revisit planning
lower-altitude revisit
health reassessment
disease classification
multi-image aggregation
uncertainty handling
manual-inspection outcomes
return-home
landing
manual takeover
pause
abort
failure logging
partial-data preservation
processing resume
mission API
persistent mission state
background processing
field-health map
farmer dashboard
final mission report
evaluation evidence
field validation
failure-case documentation
```

## 19. Planned Portfolio Extensions

The following are planned as part of the broader PlantGuard UAV portfolio:

```text
TensorRT FP16 optimization
TensorRT INT8 optimization
TensorRT calibration and benchmarking
native C++ ONNX Runtime inference
OpenCV preprocessing in C++
CMake-based native build
Python/C++ parity testing
native latency and memory benchmarks
companion-computer deployment
offline onboard screening
mobile frontend
historical field analytics
mission-to-mission comparison
season-level trend reporting
```

These extensions:

- remain modular;
- receive their own acceptance criteria;
- preserve core safety behavior;
- preserve data contracts;
- do not block the core v1.0 release unless formally promoted.

## 20. Explicit Exclusions

The following remain outside v1.0:

```text
custom airframe
custom motors
custom ESCs
custom flight controller
custom low-level stabilization
crop spraying
treatment recommendations
pesticide recommendations
chemical dosage recommendations
definitive agronomic diagnosis
multispectral sensing
hyperspectral sensing
thermal sensing
LiDAR
drone swarms
multiple simultaneous drones
multiple simultaneous fields
research-grade obstacle avoidance
unsupported rain operation
all-weather guarantee
fully unsupervised takeoff
all 132 PlantGuard diseases from wide aerial imagery
autonomous treatment actions
cloud synchronization
```

Cloud synchronization is also excluded from the planned portfolio extensions.

## 21. Frozen Verification Strategy

PlantGuard UAV shall be verified using:

```text
inspection
automated tests
simulation tests
recorded-mission tests
controlled flight tests
ground-truth evaluation
farmer workflow tests
failure injection
```

### 21.1 Release Metric Levels

Metrics use:

```text
minimum
target
stretch
```

Metric definitions remain stable even if provisional numerical values are revised after baseline measurement.

### 21.2 Real-Mission Release Gate

Before core v1.0:

```text
minimum successful end-to-end real missions: 5
target successful end-to-end real missions: 10
minimum missions across different days or conditions: 3
safe return or controlled landing: 100%
unrecovered safety-critical failures: 0
```

### 21.3 Core Release Gates

The core release requires:

```text
product gate
safety gate
flight gate
perception gate
geospatial gate
reliability gate
usability gate
documentation gate
```

Portfolio extensions do not block the core v1.0 tag.

## 22. Intentionally Unresolved Values

The following values are deliberately unresolved at Week 1 scope freeze:

```text
first field-validation crop
final drone model
final camera model
final gimbal or camera mounting method
exact platform weather rating
exact legal operating limits
exact field size
exact survey altitude
exact revisit altitude
exact survey speed
exact revisit speed
exact front overlap
exact side overlap
exact wind thresholds
exact precipitation threshold
exact minimum visibility
exact battery start threshold
exact battery reserve
exact return threshold
exact image-quality thresholds
exact screening confidence thresholds
exact disease confidence thresholds
exact multi-view agreement threshold
exact screening model architecture
exact aerial dataset composition
exact onboard-versus-ground processing split
exact companion-computer hardware
exact storage capacity
exact communication link
exact geospatial error limits after baseline
exact inference latency budget
exact retry and timeout values
```

These unresolved items are not missing requirements.

They must be resolved later using:

```text
official manufacturer documentation
applicable regulation
simulation
hardware testing
validation data
field measurements
safety testing
performance benchmarks
```

## 23. Deferred Decision Recording

When an unresolved value is finalized, record:

```text
decision ID
value selected
date
evidence
affected configuration
affected requirements
safety impact
validation result
approver
```

The detailed Week 1 documents shall not need structural rewriting when configuration values are resolved.

## 24. Scope-Change Control

After this baseline is frozen, a major scope change requires a formal change record.

Each proposed change shall include:

```text
change ID
title
requested change
reason
request date
affected documents
affected components
schedule impact
hardware impact
data impact
safety impact
testing impact
release impact
decision
decision date
```

### 24.1 Changes Requiring Formal Review

Formal review is required for:

- adding a mandatory v1.0 feature;
- removing a mandatory v1.0 feature;
- changing the primary user;
- changing the one-field/one-drone constraint;
- changing takeoff authorization;
- changing screening/revisit logic;
- changing safety precedence;
- adding new sensor categories;
- adding treatment behavior;
- adding cloud dependency;
- changing release gates;
- promoting a portfolio extension into core v1.0.

### 24.2 Changes Not Requiring Scope Review

The following may proceed through normal implementation decisions when they do not alter product intent:

- internal class names;
- function names;
- library selection;
- database schema refinement;
- route-planning algorithm choice;
- model architecture choice;
- configuration-file format;
- exact calibrated thresholds;
- hardware selection within the frozen system scope;
- UI styling;
- logging implementation details.

### 24.3 Scope-Change Decision Outcomes

A proposal may be:

```text
approved_for_v1
approved_as_extension
deferred
rejected
```

### 24.4 Default Decision

When a proposed feature is valuable but not required for the frozen user workflow, the default action is:

```text
defer to portfolio extension
```

## 25. Contradiction-Resolution Procedure

When implementation reveals a contradiction:

1. stop implementation of the affected behavior;
2. identify the conflicting statements;
3. identify the authoritative topic document;
4. preserve safety precedence;
5. issue a clarification or scope-change record;
6. update all affected documents;
7. record the decision;
8. resume implementation only after consistency is restored.

No developer shall resolve a product-level contradiction silently in code.

## 26. Cross-Document Consistency Audit

The Week 1 documents have been reviewed against the following statements.

### 26.1 Product Flow

- one saved field is selected;
- one drone is supported;
- preflight runs before takeoff;
- operator approval is mandatory;
- full-field survey occurs;
- RGB imagery is captured;
- survey screening is healthy/unhealthy/uncertain;
- suspicious sites are grouped;
- unhealthy and uncertain results enter revisit planning;
- final disease classification uses revisit imagery;
- uncertainty is preserved;
- return-home and landing occur;
- map and report are generated.

Status:

```text
consistent
```

### 26.2 Safety

- hard blockers cannot be overridden;
- manual takeover supersedes autonomy;
- abort cancels mission and normally returns home;
- return-home cancels remaining work;
- native flight-controller failsafes remain active;
- partial data is preserved;
- interrupted physical flight never auto-resumes;
- recovery requires new approval.

Status:

```text
consistent
```

### 26.3 Weather

- nominal dry mode exists;
- degraded visibility is conditional;
- light precipitation requires weather-rated hardware;
- lower altitude is adaptive, not a universal safety solution;
- VLOS, route clearance, battery, and image quality remain mandatory.

Status:

```text
consistent
```

### 26.4 Perception

- high-confidence healthy does not require revisit;
- high-confidence unhealthy requires attempted revisit;
- uncertain survey result requires attempted revisit;
- unhealthy with confident disease returns disease;
- unhealthy with uncertain disease recommends manual inspection;
- healthy after suspicious survey retains caution;
- unresolved health recommends manual inspection;
- exact thresholds are deferred to validation.

Status:

```text
consistent
```

### 26.5 Verification

- minimum/target/stretch levels are used;
- usable visual coverage is measured;
- unhealthy recall is prioritized;
- manual-inspection outcomes may count as resolved;
- at least five successful real missions are required;
- safe return or controlled landing is mandatory;
- evaluation evidence is required.

Status:

```text
consistent
```

### 26.6 Scope Boundaries

- no custom drone hardware;
- no treatment recommendations;
- no spraying;
- no multispectral/thermal/LiDAR requirement;
- no swarm;
- no cloud synchronization;
- planned TensorRT, C++, companion-computer, mobile, and historical analytics extensions remain non-blocking.

Status:

```text
consistent
```

## 27. Week 1 Deliverables

The frozen Week 1 documentation set is:

```text
docs/product_requirements.md
docs/system_scope.md
docs/data_and_decision_contracts.md
docs/safety_and_failure_policy.md
docs/verification_and_acceptance_plan.md
docs/v1_scope_baseline.md
```

## 28. Week 1 Completion Checklist

Week 1 is complete when:

- all six documents exist;
- product behavior is explicit;
- operating assumptions are explicit;
- data and decision contracts are explicit;
- safety and failure behavior is explicit;
- verification and release gates are explicit;
- terminology is canonical;
- document precedence is defined;
- unresolved values are documented;
- change control is defined;
- no known contradiction remains;
- the baseline is committed.

## 29. Recommended Commit

```bash
git add docs/product_requirements.md         docs/system_scope.md         docs/data_and_decision_contracts.md         docs/safety_and_failure_policy.md         docs/verification_and_acceptance_plan.md         docs/v1_scope_baseline.md

git commit -m "Freeze PlantGuard UAV v1.0 product scope"
```

PowerShell:

```powershell
git add docs\product_requirements.md docs\system_scope.md docs\data_and_decision_contracts.md docs\safety_and_failure_policy.md docs\verification_and_acceptance_plan.md docs\v1_scope_baseline.md
git commit -m "Freeze PlantGuard UAV v1.0 product scope"
```

## 30. Scope-Freeze Declaration

The PlantGuard UAV v1.0 product scope is frozen at the end of Week 1.

Week 2 architecture design shall treat the six Week 1 documents as authoritative inputs.

Future implementation may resolve deferred technical values, but it shall not silently alter:

```text
the farmer workflow
the survey/revisit logic
the safety hierarchy
the uncertainty policy
the v1.0 boundaries
the release gates
```

Any such change requires formal scope-change review.
