# PlantGuard UAV — Verification and Acceptance Plan

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Verification and Acceptance Plan |
| Target release | v1.0 |
| Status | Active |
| Related documents | `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md`, `docs/safety_and_failure_policy.md` |
| Last updated | 2026-07-16 |

## 1. Document Purpose

This document defines how PlantGuard UAV v1.0 will be verified, evaluated, and accepted.

It establishes:

- the metrics that must be measured;
- the minimum, target, and stretch performance levels;
- what counts as a successful survey mission;
- what counts as a successful revisit mission;
- what counts as a resolved suspicious site;
- what evidence is required before a model result is accepted;
- which features are mandatory for v1.0;
- which features are deferred beyond v1.0;
- which features remain outside project scope;
- the release gates that must pass before tagging v1.0;
- the evaluation artifacts that must exist in the repository.

The goal is to ensure that the final release is judged by reproducible evidence rather than subjective claims.

## 2. Verification Principles

PlantGuard UAV shall follow these verification principles.

### 2.1 Evidence Before Claims

No feature shall be described as complete without:

- a defined requirement;
- an observable test;
- recorded evidence;
- a documented result;
- a known limitation.

### 2.2 Safety Before Performance

No performance target may override:

- operator control;
- battery reserve;
- geofence;
- route safety;
- weather limitations;
- visual line-of-sight requirements;
- flight-controller failsafes;
- safe return or landing.

### 2.3 Valid Uncertainty Is Better Than Forced Prediction

A correct `manual_inspection_recommended` result is preferable to a confident but unsupported disease prediction.

### 2.4 Usable Coverage Matters More Than Flight-Path Coverage

An area only counts as visually covered when the system captured usable imagery for that area.

### 2.5 Field-Separated Evaluation

Training, validation, and test data shall be separated by field or mission where possible.

Nearby frames from the same flight shall not be randomly split across training and evaluation sets when that would create near-duplicate leakage.

### 2.6 Repeatability

Important results shall be reproducible from:

```text
dataset version
model version
configuration
software commit
hardware configuration
mission record
evaluation script
```

## 3. Metric Classification

Most metrics shall use three performance levels.

| Level | Meaning |
|---|---|
| Minimum | Lowest acceptable value for v1.0 release |
| Target | Expected release-quality result |
| Stretch | Excellent result worth pursuing but not required |

Some numerical values are provisional until:

- simulation baselines exist;
- the drone is selected;
- the camera is selected;
- field data is collected;
- GPS accuracy is measured;
- aerial models are trained;
- real mission duration is observed.

A provisional value may be revised after baseline measurement, but:

- the metric definition shall remain stable;
- the reason for revision shall be documented;
- the previous target shall remain visible in project history.

## 4. Verification Methods

The project shall use the following verification methods.

### 4.1 Inspection

Manual review of:

- documentation;
- configuration;
- user interface;
- logs;
- generated reports;
- source code;
- model metadata;
- saved mission artifacts.

### 4.2 Automated Test

Unit, integration, API, state-machine, route, model-contract, and failure-injection tests.

### 4.3 Simulation Test

PX4 SITL, Gazebo, MAVSDK, and simulated mission execution.

### 4.4 Recorded-Mission Test

Processing of previously captured mission data without a live aircraft.

### 4.5 Controlled Flight Test

Real drone operation in a safe, controlled field or test area.

### 4.6 Ground-Truth Evaluation

Comparison against manually reviewed:

- plant health;
- disease class;
- physical site location;
- field markers;
- revisit target;
- mission completion evidence.

### 4.7 Farmer Workflow Test

A user completes the normal workflow without terminal access or developer intervention.

## 5. Mission Outcome Definitions

### 5.1 Completed

A mission is `completed` when:

- operator authorization was recorded;
- technical preflight passed and final takeoff authorization was valid;
- the planned survey was completed;
- required imagery was captured;
- required analysis completed;
- required revisits completed or received explicit final outcomes;
- the aircraft returned or landed safely;
- mission data was preserved;
- the final map and report were generated;
- no unresolved critical system failure remains.

### 5.2 Completed With Warnings

A mission is `completed_with_warnings` when the primary product workflow succeeds, but one or more non-critical issues occurred.

Examples:

- some images were rejected;
- a small number of revisit sites could not be completed;
- optional manual inspection was recommended;
- analysis was delayed but completed successfully;
- a non-critical subsystem temporarily degraded.

### 5.3 Survey Completed, Revisit Incomplete

A mission is `survey_completed_revisit_incomplete` when:

- the survey completed;
- survey data was preserved;
- suspicious sites were generated;
- one or more required revisits were not completed;
- the aircraft returned or landed safely;
- unresolved sites were reported.

### 5.4 Survey Completed, Analysis Failed

A mission is `survey_completed_analysis_failed` when:

- the field survey completed;
- imagery and metadata were preserved;
- screening or downstream analysis did not finish;
- automatic revisit was disabled or incomplete;
- the aircraft returned or landed safely;
- processing can be resumed later.

### 5.5 Aborted

A mission is `aborted` when the operator intentionally stops autonomous work.

The mission must still:

- preserve valid data;
- record the reason;
- return home or land safely;
- report incomplete work.

### 5.6 Failed

A mission is `failed` when:

- the primary objective was not completed;
- no valid completion category applies;
- a critical subsystem or safety event prevented safe normal execution;
- the failure is explicitly logged.

A failed mission shall never be represented as completed.

## 6. Successful Survey Mission Definition

A survey mission counts as successful when:

1. operator authorization is recorded;
2. preflight passes;
3. the drone takes off safely;
4. the route covers the intended field area;
5. usable RGB imagery is captured;
6. image metadata is preserved;
7. no hard safety boundary is violated;
8. the drone returns home or performs a controlled safe landing;
9. mission artifacts are preserved;
10. the final survey status is explicit.

## 7. Successful Revisit Mission Definition

A revisit is successful when:

1. the suspicious site was selected through the defined policy;
2. the revisit waypoint was valid;
3. the drone reached the site safely;
4. the drone stabilized sufficiently;
5. at least one usable revisit image was captured;
6. the site received an explicit final outcome;
7. the revisit evidence was saved;
8. the drone continued safely or returned home.

A revisit may still produce explicit outcomes including:

```text
healthy_after_suspicious_survey
unhealthy_disease_identified
unhealthy_disease_uncertain
manual_inspection_recommended
```

All are valid reportable outcomes when they are evidence-backed, but they are not equivalent for resolution metrics.

## 8. Resolved Site Definition

A suspicious site counts as automatically resolved only when it receives one of:

```text
healthy_after_suspicious_survey
unhealthy_disease_identified
```

A site remains unresolved or requires manual action when it receives:

```text
unhealthy_disease_uncertain
health_status_unresolved
manual_inspection_recommended
revisit_not_completed
health_status_unresolved_due_to_system_failure
missing_final_result
```

`revisit_capture_failed` is recorded as a reason code for `revisit_not_completed`, not as another final status.

The site-resolution rate is:

```text
automatically resolved suspicious sites
÷
eligible suspicious sites
×
100
```

Manual-action rate and revisit-not-completed rate are reported separately. No release metric may count `manual_inspection_recommended` as an automatically resolved site.

## 9. Flight Metrics

The following shall be measured:

```text
mission completion rate
safe return or controlled landing rate
field coverage percentage
route completion percentage
image-capture success rate
revisit completion rate
operator intervention rate
abort rate
failure rate
```

### 9.1 Real-Mission Release Gate

Before v1.0:

| Requirement | Minimum | Target | Stretch |
|---|---:|---:|---:|
| Successful real end-to-end missions | 5 | 10 | 15+ |
| Missions on different days or conditions | 3 | 5 | 8+ |
| Safe return or controlled landing | 100% | 100% | 100% |
| Unrecovered safety-critical failure | 0 | 0 | 0 |
| End-to-end completion rate across registered eligible attempts | 90% | 95% | 100% |

A mission may count toward the release gate only when:

- it uses the documented workflow;
- all logs and artifacts are preserved;
- the outcome is independently reviewable;
- any warnings are documented.

The acceptance campaign register is created before the first release-candidate flight. Every eligible attempt after takeoff is included in the denominator, including aborted, failed, or incomplete attempts; results may not be cherry-picked. A test invalidated before takeoff by an external condition is retained in the register with its exclusion reason. Any repeated system-caused failure blocks release until corrected and successfully retested.

## 10. Field Coverage Metrics

The system shall measure:

```text
planned inspectable area
usable observed area
coverage gaps
duplicate coverage
coverage percentage
```

Coverage percentage is defined as:

```text
usable observed area
÷
planned inspectable area
×
100
```

Provisional targets:

| Metric | Minimum | Target | Stretch |
|---|---:|---:|---:|
| Usable field coverage | 90% | 95% | 98%+ |
| Unexplained coverage gaps | <10% | <5% | <2% |

Flight-path overlap without usable imagery shall not count as visual coverage.

The planned inspectable area is one saved field-sector boundary minus approved exclusions and safety-rejected geometry. Excluded and skipped regions are never counted as covered and remain visible in release evidence. Automatic multi-flight stitching is outside v1.0.

## 11. Image-Capture Metrics

The system shall measure:

```text
capture requests
successful captures
accepted images
rejected images
blur rate
underexposure rate
overexposure rate
obstruction rate
missing-metadata rate
corrupt-image rate
duplicate-image rate
```

Provisional targets:

| Metric | Minimum | Target | Stretch |
|---|---:|---:|---:|
| Capture success rate | 90% | 97% | 99% |
| Accepted image rate | 80% | 90% | 95% |
| Metadata completeness | 95% | 99% | 99.9% |
| Corrupt-image rate | <2% | <0.5% | <0.1% |
| Missing-location rate | <5% | <1% | <0.5% |

Final thresholds may be revised after camera and hardware baselines.

## 12. Healthy/Unhealthy Screening Metrics

The screening model shall be evaluated using:

```text
unhealthy recall
healthy recall
unhealthy precision
healthy precision
macro F1
balanced accuracy
false-negative rate
false-positive rate
confusion matrix
calibration error
uncertain-result rate
```

The priority order is:

```text
1. unhealthy recall
2. macro F1
3. unhealthy precision
4. calibration
5. overall accuracy
```

The system prioritizes unhealthy recall because missing an unhealthy region is generally more costly than revisiting an additional healthy region.

Provisional targets:

| Metric | Minimum | Target | Stretch |
|---|---:|---:|---:|
| Unhealthy recall | 0.80 | 0.90 | 0.95 |
| Macro F1 | 0.75 | 0.85 | 0.90 |
| Unhealthy precision | 0.65 | 0.80 | 0.90 |
| Balanced accuracy | 0.75 | 0.85 | 0.92 |

These values apply only after a representative aerial dataset exists.

## 13. Disease-Classification Metrics

Disease classification shall be evaluated on supported revisit-image classes using:

```text
top-1 accuracy
top-3 accuracy
macro F1
per-class recall
per-class precision
confidence calibration
high-confidence prediction precision
manual-inspection rate
non-prediction accuracy
```

The model shall not be rewarded for forcing predictions on unsupported or ambiguous images.

Provisional targets:

| Metric | Minimum | Target | Stretch |
|---|---:|---:|---:|
| Macro F1 | 0.70 | 0.80 | 0.88 |
| Top-3 accuracy | 0.85 | 0.92 | 0.96 |
| High-confidence prediction precision | 0.85 | 0.92 | 0.96 |
| Correct withholding on uncertain/unsupported cases | 0.80 | 0.90 | 0.95 |

Evaluation shall be limited to the supported crop and disease subset for the release.

## 14. Revisit Metrics

The system shall measure:

```text
sites planned
sites attempted
sites reached
sites skipped
usable revisit images
resolved sites
sites requiring manual inspection
```

Provisional targets:

| Metric | Minimum | Target | Stretch |
|---|---:|---:|---:|
| Revisit reach rate | 85% | 95% | 98% |
| Usable revisit capture rate | 80% | 95% | 98% |
| Site-resolution rate | 85% | 95% | 98% |
| Unexplained revisit failure rate | <10% | <5% | <2% |

Sites skipped for documented safety or battery reasons shall be reported separately from unexplained failures.

## 15. Geospatial Metrics

The system shall measure:

```text
survey-observation location error
suspicious-site location error
duplicate-site rate
site-clustering precision
site-clustering recall
revisit waypoint error
capture-near-target success rate
```

Recommended validation method:

1. place known ground markers;
2. record their measured coordinates;
3. fly the survey;
4. map detected locations;
5. compare predicted and measured positions;
6. report median, mean, and 95th-percentile error.

Provisional targets:

| Metric | Minimum | Target | Stretch |
|---|---:|---:|---:|
| Median suspicious-site location error | ≤5 m | ≤2 m | ≤1 m |
| 95th-percentile location error | ≤10 m | ≤5 m | ≤2 m |
| Duplicate-site rate | ≤15% | ≤5% | ≤2% |
| Capture-near-target success | 85% | 95% | 98% |

Final values depend on GPS, camera geometry, altitude, and field conditions.

## 16. System Performance Metrics

The system shall measure:

```text
image-validation throughput
tiling throughput
screening latency
classification latency
site-clustering duration
map-generation duration
report-generation duration
total mission-processing duration
peak memory
worker failure rate
API failure rate
resume success rate
```

### 16.1 Performance Acceptance Principles

The v1.0 system shall:

- process a complete recorded mission without manual per-image intervention;
- preserve progress during interruption;
- resume processing from checkpoints;
- avoid silent data loss;
- log all stage failures;
- report stage timing;
- report model inference latency;
- expose system health.

### 16.2 In-Mission Analysis Timing

The initial analysis should complete early enough to leave sufficient battery for:

```text
selected revisit targets
+
return-to-home
+
landing
+
reserve
```

If it cannot finish within the safe time budget:

```text
do not begin revisit
→ return home
→ continue analysis later
```

An exact in-mission latency target shall be derived after baseline measurements.

## 17. API Verification

The API shall be verified for:

```text
field creation and retrieval
mission creation
mission start
mission abort
return-home command
mission status
detection retrieval
map retrieval
health check
model metadata
invalid input handling
authentication or access policy where implemented
```

Acceptance requirements:

- valid requests return documented responses;
- invalid requests return explicit errors;
- long-running work is asynchronous where required;
- job status is persisted;
- failed jobs retain error details;
- API failure does not remove aircraft safety.

## 18. Dashboard Acceptance

The farmer shall be able to:

- select a saved field;
- see drone connection;
- see preflight readiness;
- approve takeoff;
- see mission state;
- see mission progress;
- see battery and warnings;
- pause the mission;
- explicitly resume a safely held mission when revalidation permits;
- abort the mission;
- command return-home;
- see field coverage;
- see suspicious sites;
- see revisit status;
- see final health status;
- see disease prediction;
- see confidence;
- see manual-inspection recommendations;
- open supporting images;
- view the final field map;
- view the final report.

The farmer shall not need:

```text
terminal access
Python knowledge
PX4 knowledge
ROS 2 knowledge
manual coordinate entry
model file paths
database access
```

## 19. Safety Verification

The following behaviors shall be demonstrated in simulation, integration tests, or controlled real tests where appropriate:

- takeoff blocked without operator approval;
- technical preflight result remains independent of missing approval;
- stale approval or changed preflight inputs invalidate final takeoff authorization;
- takeoff blocked with invalid field boundary;
- takeoff blocked with invalid home position;
- takeoff blocked with insufficient battery;
- takeoff blocked with unsupported weather;
- takeoff blocked when required camera or model is unavailable;
- invalid revisit waypoint rejected;
- geofence retained;
- manual takeover stops autonomy;
- abort cancels remaining work and returns home;
- return-home cancels remaining mission work;
- camera failure produces the documented response;
- screening failure disables automatic revisit;
- disease-classifier failure preserves revisit evidence;
- dashboard failure does not remove flight safety;
- backend failure does not remove manual control;
- telemetry loss follows native failsafe policy;
- interrupted flight does not restart automatically;
- recovery mission requires new preflight and approval;
- pause converts to hold only when safe and resume requires explicit revalidation;
- resume is rejected after restart, manual takeover, or loss of authoritative context;
- partial data survives mission interruption.

## 20. Failure-Injection Verification

The project shall test at minimum:

```text
camera disconnect
corrupt image
missing metadata
screening worker crash
classification worker crash
database unavailable
dashboard unavailable
telemetry interruption
GPS degradation
low battery
invalid route
invalid revisit waypoint
wind threshold exceeded
dry-daylight envelope violation
operator abort
manual takeover
```

Each test shall verify:

```text
detected condition
severity
state transition
system action
operator message
preserved artifacts
final mission status
recovery behavior
```

## 21. Data Integrity Verification

The project shall verify that:

- every mission has a unique identifier;
- every image belongs to one mission;
- every observation references a source image;
- every suspicious site references supporting observations;
- every revisit image references one suspicious site;
- every final result references model and configuration versions;
- every report references the correct mission;
- no final result exists without source evidence;
- incomplete missions do not appear complete;
- rerunning a completed processing stage does not corrupt previous outputs.

## 22. Model Contract Verification

Each deployed model shall be tested for:

```text
input shape
input dtype
input normalization
class ordering
output shape
output dtype
confidence range
unknown class handling
metadata availability
model version
preprocessing version
```

Invalid outputs such as:

```text
NaN
infinite confidence
negative confidence
confidence above 1
unknown class identifier
wrong output shape
missing metadata
```

shall be rejected and logged.

## 23. Evidence Required Before Resolving a Site

A site may be marked `healthy_after_suspicious_survey` only when:

- at least one accepted revisit image exists;
- health reassessment is high-confidence healthy;
- supporting evidence is stored;
- the cautionary advisory is retained.

A site may be marked `unhealthy_disease_identified` only when:

- health is high-confidence unhealthy;
- disease confidence meets the configured threshold;
- required image-quality conditions pass;
- required multi-view agreement passes where configured;
- model and configuration versions are recorded.

A site may be marked `unhealthy_disease_uncertain` when:

- health is high-confidence unhealthy;
- disease evidence is insufficient;
- manual inspection is recommended;
- the reason is saved.

A site may be marked `manual_inspection_recommended` when:

- health remains uncertain;
- disease remains uncertain;
- image quality is insufficient;
- revisit cannot be completed;
- the crop or condition is unsupported.

## 24. Mandatory v1.0 Features

The following are mandatory for PlantGuard UAV v1.0:

```text
saved field-sector selection
operator-approved takeoff
technical preflight and final takeoff authorization
one-drone mission control
planned-inspectable-area survey
approved exclusion zones and skipped-area reporting
geotagged RGB image capture
image-quality validation
healthy/unhealthy/uncertain screening
suspicious-site grouping
automatic revisit planning
lower-altitude revisit
disease classification
multi-image result aggregation
uncertainty handling
manual-inspection outcome
return-home
landing
manual takeover
pause
explicit safe resume
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
failure-case documentation
one configured crop or crop family
limited validated disease taxonomy
dry daylight operation
```

## 25. Deferred Post-v1 Capabilities

The following capabilities are deferred beyond the core PlantGuard UAV v1.0 release unless they are explicitly promoted through product change control.

### 25.1 TensorRT Optimization

Planned work may include:

- FP16 TensorRT inference;
- INT8 TensorRT inference;
- calibration workflow;
- ONNX versus TensorRT accuracy comparison;
- latency and throughput benchmarks;
- GPU memory measurements;
- deployment notes.

### 25.2 Native C++ Inference

Planned work may include:

- C++ inference service or module;
- ONNX Runtime C++ integration;
- OpenCV preprocessing;
- batch processing;
- memory reuse;
- latency benchmarking;
- Python-versus-C++ parity testing;
- native build with CMake;
- automated tests.

### 25.3 Conditionally Promoted Companion-Computer Deployment

Companion deployment remains deferred when the ground-station path passes the same-flight transfer, inference, revisit-decision, and energy gate. If the ground path fails, release is blocked until a companion path is formally promoted and qualified. Qualification work includes:

- onboard lightweight health screening;
- local mission-state synchronization;
- image buffering;
- offline operation;
- ground-station fallback;
- hardware resource monitoring;
- thermal and power testing;
- failure recovery.

### 25.4 Mobile Frontend

Planned work may include:

- field selection;
- live mission state;
- alerts;
- abort and return-home controls;
- results review;
- image previews;
- field map;
- offline-friendly operation.

A mobile-native frontend is an extension; the core v1.0 farmer dashboard may remain web-based.

### 25.5 Historical Field Analytics

Planned work may include:

- mission-to-mission comparison;
- repeated suspicious-site tracking;
- disease trend visualization;
- field-health history;
- severity trend;
- season-level summaries;
- export for agronomic review.

### 25.6 Route and Operating-Envelope Expansion

The following remain deferred unless promoted through change control with their own safety and field evidence:

- priority-zone route customization;
- guided route customization;
- custom route drafts;
- automatic multi-flight stitching;
- additional production crop taxonomies;
- fog, mist, rain, precipitation, or degraded-visibility operation.

### 25.7 Extension Acceptance Rule

Deferred post-v1 capabilities must:

- remain modular;
- have their own acceptance criteria;
- preserve the core data contracts;
- preserve safety behavior;
- include reproducible benchmarks;
- not silently alter model preprocessing or class order;
- not delay the core v1.0 release unless formally moved into mandatory scope.

## 26. Explicitly Excluded Features

The following remain outside PlantGuard UAV v1.0 and are not included in the post-v1 product roadmap:

```text
cloud synchronization
custom airframe
custom motors
custom ESCs
custom flight controller
custom low-level stabilization
crop spraying
pesticide recommendations
chemical dosage recommendations
multispectral imaging
hyperspectral imaging
thermal imaging
LiDAR
drone swarms
multiple simultaneous drones
multiple simultaneous fields
research-grade obstacle avoidance
unsupported rain operation
all-weather guarantee
fully unsupervised takeoff
guaranteed diagnosis of all PlantGuard classes from high altitude
autonomous treatment actions
```

Cloud synchronization is explicitly excluded from the deferred post-v1 capabilities.

## 27. Required Repository Evaluation Artifacts

Before final release, the repository shall contain:

```text
docs/evaluation_report.md
docs/failure_case_report.md
docs/model_card_screening.md
docs/model_card_disease_classifier.md
docs/field_test_protocol.md
docs/field_test_results.md
docs/system_benchmark_report.md
docs/requirements_traceability_matrix.md
```

The repository should also include machine-readable evidence such as:

```text
metrics.json
mission summaries
confusion matrices
calibration results
latency results
memory results
geospatial error results
failure-injection results
model metadata
configuration snapshots
```

## 28. Requirements Traceability

Each major requirement shall eventually map to:

```text
requirement ID
implementation component
verification method
test identifier
evidence location
result
release status
```

Example:

| Requirement | Verification | Evidence |
|---|---|---|
| Operator approval required | Integration test | Linked preflight, approval, and final-authorization log |
| Invalid revisit waypoint rejected | Unit/integration test | Route validation report |
| Screening failure disables revisit | Failure injection | Mission event log |
| Disease prediction traceable | Data integrity test | Final-site record |
| Farmer can abort mission | Simulation/field test | Dashboard and flight log |

## 29. Release Gates

PlantGuard UAV v1.0 shall not be tagged until all mandatory gates pass.

### 29.1 Product Gate

The complete one-button workflow functions end to end:

```text
select field
→ select field sector and exclusions
→ technical preflight
→ approve takeoff
→ final takeoff authorization
→ survey
→ screen
→ group sites
→ revisit
→ classify
→ return
→ land
→ report
```

### 29.2 Safety Gate

All mandatory technical-preflight, final-authorization, pause/resume, abort, return-home, manual-takeover, geofence, battery, dry-daylight-envelope, and failure policies have been demonstrated.

### 29.3 Flight Gate

At least five successful real end-to-end missions have been completed across at least three days within the qualified production envelope. Every eligible release-candidate attempt is registered before flight and included in the completion-rate denominator.

### 29.4 Perception Gate

The screening and disease-classification models meet the final approved thresholds on field-separated test data.

### 29.5 Geospatial Gate

Suspicious sites can be mapped and revisited within the final approved error range using the frozen CRS, axis-order, altitude-reference, coordinate-frame, and time-synchronization contracts.

### 29.6 Reliability Gate

The system demonstrates:

- no silent data loss;
- checkpointed processing;
- processing recovery;
- explicit failure states;
- preserved partial missions.
- separate and reconstructable workflow, mission-activity, vehicle, and processing-job states.

### 29.7 Usability Gate

A farmer can complete the primary workflow without terminal access.

### 29.8 Documentation Gate

The repository contains:

- setup instructions;
- architecture documentation;
- model cards;
- evaluation report;
- field-test protocol;
- field-test results;
- failure-case report;
- benchmark report;
- limitations;
- deployment and operations runbook.

### 29.9 Post-v1 Capability Gate

Deferred post-v1 capabilities are not required for the core v1.0 tag.

They may receive separate tags or milestone releases after core v1.0.

## 30. Final Definition of Done

PlantGuard UAV v1.0 is complete only when:

- a saved field can be selected;
- technical preflight validates the mission independently of approval;
- unsafe starts are blocked;
- operator approval and final takeoff authorization are required;
- one drone surveys the planned inspectable area of one field sector;
- usable geotagged RGB images are captured;
- image quality is evaluated;
- healthy, unhealthy, and uncertain screening works;
- suspicious observations are grouped;
- high-confidence unhealthy and uncertain observations enter revisit planning;
- revisit targets are generated automatically;
- safe revisit targets are attempted;
- higher-detail images are captured;
- final health status is produced;
- disease prediction is produced when supported;
- low-confidence disease results are withheld;
- manual inspection is recommended when appropriate;
- the aircraft returns or lands safely;
- the farmer receives a field map and report;
- manual takeover, abort, pause, and return-home work;
- an explicitly requested resume works only from a safe confirmed hold after current revalidation;
- major failure scenarios have been tested;
- partial mission data survives interruption;
- processing resumes from checkpoints;
- at least five real end-to-end missions have succeeded;
- evaluation metrics are published;
- model limitations are documented;
- failure cases are documented;
- the repository contains reproducible setup and evidence.
- the selected ground or qualified companion topology passes the same-flight transfer, inference, revisit-decision, and energy gate.

## 31. Verification-Baseline Acceptance Criteria

The verification baseline is complete when:

- metric categories are defined;
- minimum, target, and stretch levels are adopted;
- flight success is defined;
- survey success is defined;
- revisit success is defined;
- resolved-site behavior is defined;
- image-quality metrics are defined;
- screening metrics are defined;
- classification metrics are defined;
- geospatial metrics are defined;
- system-performance metrics are defined;
- API and dashboard acceptance are defined;
- safety verification is defined;
- failure-injection coverage is defined;
- release gates are explicit;
- mandatory v1.0 features are frozen;
- deferred post-v1 capabilities are recorded;
- cloud synchronization is explicitly excluded;
- required repository evidence is identified;
- the final definition of done is measurable.

## 32. Final Acceptance Statement

PlantGuard UAV v1.0 shall be accepted only when the system demonstrates safe, repeatable, traceable, and evidence-backed autonomous field inspection.

The release must prove that it can:

```text
survey the planned inspectable area of one field sector
capture usable evidence
detect suspicious crop regions
revisit them safely
produce honest health and disease outcomes
preserve uncertainty
return safely
and present actionable inspection results to the farmer
```

TensorRT optimization, native C++ inference, companion-computer deployment, a mobile frontend, and historical field analytics are deferred post-v1 capabilities.

Cloud synchronization is not part of the planned project scope.
