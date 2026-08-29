# PlantGuard UAV — Product Requirements

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Product Requirements |
| Target release | v1.0 |
| Status | Active |
| Primary user | Farmer |
| Mission scope | One predefined field and one drone at a time |
| Sensor scope | RGB camera |
| Product owner | Project maintainer |
| Last updated | 2026-07-16 |

## 1. Document Purpose

This document defines the product requirements for PlantGuard UAV v1.0.

It specifies:

- the problem being solved;
- the intended user;
- the complete user workflow;
- the system's required behavior;
- the outputs presented to the farmer;
- the decisions the system may automate;
- the decisions that remain under human control;
- the expected handling of confidence and uncertainty;
- the acceptance criteria for the final product.

Detailed flight limits, environmental assumptions, safety rules, and failure-response behavior are maintained in `docs/system_scope.md`.

## 2. Product Overview

PlantGuard UAV is an operator-authorized autonomous RGB field-inspection system.

It is designed to inspect one predefined agricultural field sector at a time using one programmable drone. The system surveys the planned inspectable area, captures geotagged imagery, performs an initial healthy-versus-unhealthy screening pass, groups suspicious observations into physical inspection sites, revisits those sites at lower altitude, and attempts disease classification using higher-detail images.

After the mission, the drone returns home and the farmer receives the results through an application dashboard.

The dashboard presents:

- field coverage;
- healthy and unhealthy observations;
- suspicious-site locations;
- revisit status;
- likely disease predictions;
- confidence scores;
- uncertain cases;
- image previews;
- mission-level summary metrics.

PlantGuard UAV supports decision-making and field inspection. It does not provide definitive agronomic diagnosis or treatment recommendations in v1.0.

## 3. Problem Statement

Manual inspection of a large agricultural field is slow, physically demanding, difficult to repeat consistently, and prone to missed problem areas.

A farmer may need to inspect many plants across a large area before locating a small number of unhealthy regions. Even after identifying a suspicious plant, disease recognition may remain uncertain without a closer image or expert review.

PlantGuard UAV addresses this problem through a two-pass inspection workflow:

1. survey the entire predefined field;
2. identify healthy and unhealthy-looking crop regions;
3. group suspicious observations into inspection sites;
4. revisit those sites at lower altitude;
5. capture clearer images;
6. estimate the most likely disease and report confidence;
7. present the results on a field map for the farmer.

The product is intended to reduce inspection effort and help farmers prioritize where manual attention is required.

## 4. Primary User

The primary user is a farmer.

The farmer is not expected to understand:

- PX4;
- ROS 2;
- MAVSDK;
- ONNX Runtime;
- object-detection thresholds;
- model preprocessing;
- GeoJSON;
- flight-path algorithms;
- internal mission-state transitions.

The farmer interacts with the system through an application dashboard that uses clear, non-technical language.

## 5. User and Mission Assumptions

PlantGuard UAV v1.0 assumes:

- one farmer or authorized operator controls the mission;
- one drone is connected at a time;
- one predefined field sector is processed at a time;
- the field boundary, inspectable sector, and approved exclusion zones are saved before the mission begins;
- the operator explicitly approves every takeoff;
- the drone surveys the planned inspectable area of that sector;
- suspicious or unhealthy sites are revisited for closer inspection;
- the system uses RGB imagery;
- the production release is validated for one configured crop or crop family and a limited supported disease taxonomy;
- missions begin only in dry daylight conditions with adequate visibility and supported wind;
- treatment recommendations are excluded;
- uncertain cases are shown honestly instead of forcing a disease prediction.

## 6. Primary User Journey

The intended end-to-end user journey is:

1. The farmer opens the PlantGuard UAV application.
2. The farmer selects a previously saved field.
3. The system connects to one supported drone.
4. The system loads the field boundary and mission configuration.
5. The system performs technical preflight checks without treating missing approval as a technical failure.
6. The application displays technical readiness, warnings, and blockers.
7. The authorized operator approves takeoff against the current valid preflight snapshot.
8. The drone takes off automatically.
9. The drone follows an automatically generated survey route covering the planned inspectable area.
10. The camera captures geotagged RGB images.
11. The system screens visible crop regions as healthy or unhealthy.
12. Unhealthy or suspicious observations are grouped into physical inspection sites.
13. The system prioritizes sites for revisit.
14. A lower-altitude revisit mission is generated.
15. The drone revisits selected suspicious sites.
16. The drone stabilizes and captures higher-detail images.
17. PlantGuard attempts disease classification using the revisit images.
18. The system returns the likely disease and confidence when evidence is sufficient.
19. Ambiguous or low-quality cases are marked for manual inspection.
20. The drone returns home and lands.
21. The system finalizes the mission results.
22. The farmer receives a field map, diagnosis metrics, image previews, and a mission report.

## 7. Core Use Cases

### 7.1 Select a Field

The farmer selects one previously saved field.

The field record must contain enough information to identify:

- the field boundary;
- the home or takeoff area;
- the field identifier;
- the mission configuration associated with that field.

### 7.2 Review System Readiness

Before takeoff, the farmer must be shown a clear readiness summary.

The application must indicate whether:

- the drone is connected;
- the field configuration is valid;
- the mission can be generated;
- required models are available;
- the camera is available;
- the system is ready for operator approval.

Detailed flight-safety requirements are defined in `docs/system_scope.md`.

### 7.3 Authorize Takeoff

The drone must not take off without explicit operator approval.

The application must provide a clear action such as:

```text
Start Field Scan
```

The action must only be enabled when required preflight checks pass.

### 7.4 Survey the Planned Inspectable Area

The system must generate and execute a route for one predefined field sector. The planned inspectable area is the saved sector boundary minus approved exclusion zones and any region rejected by safety validation.

The automatic survey must target the complete planned inspectable area. A mission meets the minimum production coverage gate only when at least 90% of that area has usable inspection coverage; the target is at least 95%. Every skipped or unusable region must remain visible in the map and report.

Automatic multi-flight stitching is not part of v1.0. A field that cannot fit the validated survey, same-flight decision, revisit, return, landing, and reserve envelope must be divided into separately approved sectors and missions.

The survey must:

- cover the field systematically;
- collect geotagged RGB imagery;
- retain capture timestamps;
- retain sufficient information to associate each image with its location;
- record mission progress.

### 7.5 Screen Crop Health

The initial perception stage must distinguish between:

```text
healthy
unhealthy
```

This stage is a screening stage, not a final disease diagnosis.

The system must retain:

- the source image;
- the crop region or tile;
- the location;
- the health-screening result;
- the screening confidence;
- any relevant image-quality status.

### 7.6 Group Suspicious Observations

Multiple images may contain the same physical plant or unhealthy region.

The system must group nearby or overlapping unhealthy observations into suspicious sites so that one physical area is not reported repeatedly.

### 7.7 Revisit Suspicious Sites

The system must generate a lower-altitude revisit plan for selected suspicious sites.

The revisit stage must:

- prioritize useful sites;
- avoid revisiting duplicate observations;
- capture higher-detail images;
- retain location and image metadata;
- record whether each revisit succeeded or failed.

### 7.8 Classify Likely Disease

For each revisited unhealthy site, the system must attempt to predict the likely disease.

A successful classification result must include:

- predicted disease;
- confidence score;
- source revisit image or images;
- site identifier;
- health status;
- model version;
- classification timestamp.

### 7.9 Handle Uncertain Results

The system must not force a disease label when:

- image resolution is insufficient;
- the image is too blurry;
- the plant region is too small;
- the available views disagree;
- model confidence is below the accepted threshold;
- the image does not contain enough useful visual evidence.

Such cases must be marked with a clear status, such as:

```text
manual_inspection_recommended
```

and an explicit reason.

### 7.10 Review Mission Results

After the mission, the farmer must be able to review:

- the surveyed field;
- the flight path;
- field coverage;
- healthy and unhealthy observations;
- suspicious sites;
- revisit status;
- final disease predictions;
- confidence scores;
- uncertain cases;
- image previews;
- mission summary metrics.

## 8. Functional Requirements

### 8.1 Field Management

- **PR-FIELD-001:** The system shall allow the farmer to select one previously saved field.
- **PR-FIELD-002:** The system shall load the field boundary before mission generation.
- **PR-FIELD-003:** The system shall support one active field mission at a time.
- **PR-FIELD-004:** The system shall reject mission creation when the saved field record is invalid or incomplete.

### 8.2 Drone and Mission Control

- **PR-MISSION-001:** The system shall support one connected drone at a time.
- **PR-MISSION-002:** The system shall require operator approval before takeoff.
- **PR-MISSION-003:** The system shall generate a route targeting the complete planned inspectable area of one saved field sector.
- **PR-MISSION-004:** The system shall track mission progress.
- **PR-MISSION-005:** The system shall support operator-initiated abort and return-to-home actions.
- **PR-MISSION-006:** The system shall record mission start, end, duration, and completion status.
- **PR-MISSION-007:** The drone shall return home after the mission or when required by the safety policy.
- **PR-MISSION-008:** The system shall retain partial mission data when a mission does not complete.
- **PR-MISSION-009:** The system shall support approved exclusion zones and shall never count excluded regions as inspected.
- **PR-MISSION-010:** The system shall reject a mission that cannot fit the validated survey, same-flight decision, revisit, return, landing, and battery-reserve envelope.
- **PR-MISSION-011:** An operator pause request shall enter a confirmed hold only when the Safety Supervisor determines holding is safe.
- **PR-MISSION-012:** Resuming a held mission shall require explicit operator action and current safety revalidation; restart, manual takeover, or lost authority shall require a new recovery mission.

### 8.3 Image Capture and Traceability

- **PR-IMAGE-001:** The system shall capture RGB images during the field survey.
- **PR-IMAGE-002:** Every accepted image shall be associated with a mission identifier.
- **PR-IMAGE-003:** Every accepted geospatial observation shall retain a UTC capture time, synchronized vehicle pose, coordinate reference, altitude reference, and uncertainty metadata.
- **PR-IMAGE-004:** The system shall record image-quality status.
- **PR-IMAGE-005:** The system shall retain the relationship between a cropped region and its source image.
- **PR-IMAGE-006:** The system shall record failed or missing captures.

### 8.4 Healthy/Unhealthy Screening

- **PR-SCREEN-001:** The initial screening stage shall classify usable crop observations as healthy or unhealthy.
- **PR-SCREEN-002:** The screening result shall include a confidence score.
- **PR-SCREEN-003:** The system shall preserve the location and source evidence for every unhealthy observation.
- **PR-SCREEN-004:** The screening stage shall not claim a specific disease.
- **PR-SCREEN-005:** The system shall allow unusable observations to be rejected without assigning a health label.

### 8.5 Suspicious-Site Formation

- **PR-SITE-001:** The system shall group nearby or overlapping unhealthy observations into suspicious sites.
- **PR-SITE-002:** Each suspicious site shall receive a unique identifier.
- **PR-SITE-003:** Each suspicious site shall retain all supporting observations.
- **PR-SITE-004:** The system shall avoid reporting obvious duplicates as separate sites.
- **PR-SITE-005:** The system shall record the reason a site was selected or not selected for revisit.

### 8.6 Revisit Planning

- **PR-REVISIT-001:** The system shall generate revisit targets from selected suspicious sites.
- **PR-REVISIT-002:** Revisit targets shall include location and target altitude.
- **PR-REVISIT-003:** The system shall record revisit success, failure, or skip status.
- **PR-REVISIT-004:** The system shall not require manual coordinate entry for normal revisit generation.
- **PR-REVISIT-005:** The system shall preserve unvisited sites in the final report.

### 8.7 Disease Classification

- **PR-CLASS-001:** The final classification stage shall operate on revisit imagery.
- **PR-CLASS-002:** The final result shall include the predicted disease and confidence when evidence is sufficient.
- **PR-CLASS-003:** The system shall retain the supporting image or images.
- **PR-CLASS-004:** The system shall record the model version used for classification.
- **PR-CLASS-005:** The system shall support a non-prediction outcome when evidence is insufficient.
- **PR-CLASS-006:** The system shall not present a low-confidence result as certain.

### 8.8 Farmer Dashboard

- **PR-DASH-001:** The farmer shall be able to select a saved field.
- **PR-DASH-002:** The dashboard shall show drone connection and mission readiness.
- **PR-DASH-003:** The dashboard shall provide a Start Field Scan action.
- **PR-DASH-004:** The dashboard shall provide Abort Mission and Return Home controls.
- **PR-DASH-005:** The dashboard shall show mission state and progress.
- **PR-DASH-006:** The dashboard shall display the final field-health map.
- **PR-DASH-007:** The dashboard shall display healthy and unhealthy counts or percentages.
- **PR-DASH-008:** The dashboard shall display suspicious-site locations.
- **PR-DASH-009:** The dashboard shall display final disease predictions and confidence.
- **PR-DASH-010:** The dashboard shall display uncertain or manual-inspection cases.
- **PR-DASH-011:** The dashboard shall display captured evidence images.
- **PR-DASH-012:** The dashboard shall display mission summary metrics.
- **PR-DASH-013:** The dashboard shall provide Pause Mission when the current vehicle mode and safety policy permit it.
- **PR-DASH-014:** The dashboard shall provide Resume Mission only for a confirmed safe hold and shall display rejection or return-home decisions explicitly.

### 8.9 Reporting

- **PR-REPORT-001:** The system shall generate a mission summary after processing completes.
- **PR-REPORT-002:** The report shall include the field identifier and mission identifier.
- **PR-REPORT-003:** The report shall include coverage and image-capture statistics.
- **PR-REPORT-004:** The report shall include healthy and unhealthy screening metrics.
- **PR-REPORT-005:** The report shall include suspicious sites and revisit status.
- **PR-REPORT-006:** The report shall include final disease predictions with confidence.
- **PR-REPORT-007:** The report shall include uncertain cases and reasons.
- **PR-REPORT-008:** The report shall include model and configuration metadata.
- **PR-REPORT-009:** The report shall be viewable through the farmer application.
- **PR-REPORT-010:** Machine-readable mission results shall be exportable for engineering analysis.

## 9. Non-Functional Requirements

### 9.1 Reliability

- **PR-NFR-REL-001:** Mission data shall not be silently discarded after a software failure.
- **PR-NFR-REL-002:** Partial results shall remain available when a mission is aborted or incomplete.
- **PR-NFR-REL-003:** Every failed processing stage shall produce an explicit error state.
- **PR-NFR-REL-004:** Re-running a completed processing stage shall not corrupt previous results.

### 9.2 Traceability

- **PR-NFR-TRACE-001:** Every mission shall have a unique identifier.
- **PR-NFR-TRACE-002:** Every suspicious site shall have a unique identifier.
- **PR-NFR-TRACE-003:** Every prediction shall be traceable to its source image, model version, and configuration.
- **PR-NFR-TRACE-004:** Every final report shall identify the software and model versions used.

### 9.3 Usability

- **PR-NFR-USE-001:** The primary workflow shall not require terminal commands from the farmer.
- **PR-NFR-USE-002:** Technical errors shall be translated into understandable user messages.
- **PR-NFR-USE-003:** The farmer shall be able to identify which areas require attention without reading raw model outputs.
- **PR-NFR-USE-004:** Confidence and uncertainty shall be displayed in a way that does not imply certainty where none exists.

### 9.4 Maintainability

- **PR-NFR-MAINT-001:** Mission planning, drone control, perception, mapping, reporting, and user-interface logic shall remain modular.
- **PR-NFR-MAINT-002:** Model-specific preprocessing shall be stored with model metadata.
- **PR-NFR-MAINT-003:** Product requirements shall remain testable through explicit requirement identifiers.
- **PR-NFR-MAINT-004:** The core mission-processing pipeline shall be callable independently of the user interface.

### 9.5 Performance

- **PR-NFR-PERF-001:** The system shall report processing duration for every mission.
- **PR-NFR-PERF-002:** The system shall report model inference latency.
- **PR-NFR-PERF-003:** The system shall support processing a complete recorded mission without manual per-image intervention.
- **PR-NFR-PERF-004:** Detailed numerical release targets shall be set after baseline data and hardware measurements are available.

## 10. System Inputs

The product may consume:

- saved field boundary;
- field identifier;
- home or takeoff position;
- survey configuration;
- revisit configuration;
- operator authorization;
- drone connection state;
- drone telemetry;
- camera images;
- image-capture timestamps;
- geographic position;
- altitude;
- vehicle attitude;
- camera metadata;
- perception model configuration;
- model artifacts;
- decision thresholds;
- farmer-issued abort or return-home commands.

## 11. System Outputs

The product shall produce or expose:

- mission state;
- preflight readiness;
- survey route;
- flight path;
- mission progress;
- image manifest;
- rejected-image records;
- healthy observations;
- unhealthy observations;
- suspicious-site records;
- revisit targets;
- revisit results;
- final disease predictions;
- confidence scores;
- uncertainty statuses;
- manual-inspection flags;
- annotated evidence images;
- field-health map;
- mission summary metrics;
- machine-readable exports;
- operator-facing final report.

## 12. Automated Decisions

PlantGuard UAV may automatically decide:

- whether a mission configuration is structurally valid;
- whether an image is usable for perception;
- whether an observation appears healthy or unhealthy;
- whether multiple observations likely represent the same physical site;
- whether a site should be considered for revisit;
- the practical revisit order;
- whether a revisit image is sufficient for disease classification;
- the most likely disease class;
- whether confidence is too low to issue a disease prediction;
- whether a result should be marked for manual inspection;
- whether mission processing can resume from saved progress.

Automated decisions must remain traceable to saved evidence and configuration.

## 13. Human-Controlled Decisions

The following decisions remain under human control:

- selecting the field;
- approving takeoff;
- aborting the mission;
- commanding return-to-home;
- taking manual control;
- deciding whether to act on a disease prediction;
- deciding whether to obtain expert agronomic review;
- deciding whether and how to treat the crop.

The system shall not override an operator-issued abort or return-home command.

## 14. Confidence and Uncertainty Policy

### 14.1 Healthy/Unhealthy Screening

A screening result shall include:

- label: `healthy` or `unhealthy`;
- confidence;
- image-quality status;
- source evidence;
- geographic context.

### 14.2 Disease Classification

A disease result shall include:

- predicted disease;
- confidence;
- supporting image or images;
- site identifier;
- model version.

### 14.3 Non-Prediction Outcomes

The system shall support explicit non-prediction outcomes, including:

```text
insufficient_visual_resolution
image_quality_rejected
model_confidence_too_low
inconsistent_views
unsupported_crop_or_condition
manual_inspection_recommended
```

### 14.4 Presentation Rules

The application shall:

- distinguish screening confidence from disease-classification confidence;
- avoid describing model output as guaranteed;
- show uncertain cases separately;
- preserve the reason a prediction was withheld;
- allow the farmer to review supporting images.

## 15. Farmer-Facing Dashboard Requirements

The final application should provide the following views.

### 15.1 Field Selection

- saved-field list;
- field name;
- field boundary preview;
- selected drone;
- latest mission status.

### 15.2 Preflight View

- drone connection;
- mission readiness;
- camera readiness;
- model readiness;
- blocking errors;
- Start Field Scan control.

### 15.3 Live Mission View

- current mission state;
- progress percentage;
- current drone location;
- battery status;
- image count;
- suspicious observations found;
- suspicious sites formed;
- revisit progress;
- warnings;
- Abort Mission;
- Return Home.

### 15.4 Results View

- field-health map;
- survey flight path;
- healthy/unhealthy distribution;
- suspicious-site markers;
- revisit status;
- final disease prediction per site;
- confidence;
- uncertainty or manual-inspection flag;
- image previews;
- mission summary;
- export options.

## 16. Expected Mission Metrics

The final product shall make room for the following metrics.

### 16.1 Mission Metrics

- mission duration;
- field coverage;
- images requested;
- images captured;
- images accepted;
- images rejected;
- survey completion status;
- revisit completion status;
- return-home status.

### 16.2 Screening Metrics

- healthy observation count;
- unhealthy observation count;
- healthy percentage;
- unhealthy percentage;
- rejected observation count;
- average screening confidence.

### 16.3 Suspicious-Site Metrics

- total suspicious observations;
- total grouped sites;
- sites selected for revisit;
- sites successfully revisited;
- sites skipped;
- sites requiring manual inspection.

### 16.4 Classification Metrics

- sites with final disease predictions;
- disease distribution;
- confidence distribution;
- uncertain-result count;
- average classification confidence;
- supporting image count per site.

### 16.5 Engineering Metrics

- image-processing duration;
- screening inference latency;
- final-classification latency;
- total mission-processing duration;
- model versions;
- software version;
- error count.

## 17. Product Boundaries

### 17.1 Included in v1.0

PlantGuard UAV v1.0 includes:

- one ready-made programmable drone;
- one field at a time;
- one drone at a time;
- predefined field boundaries;
- one predefined field sector per mission;
- approved exclusion zones;
- operator-authorized takeoff;
- automatic survey of the planned inspectable area;
- RGB image capture;
- geotagged mission data;
- healthy/unhealthy screening;
- suspicious-site grouping;
- automatic revisit planning;
- lower-altitude revisit image capture;
- disease classification with confidence;
- uncertainty handling;
- automatic return-home and landing;
- farmer-facing dashboard;
- field-health map;
- final mission report;
- manual takeover, pause/resume, abort, and return-home controls;
- one configured crop or crop family with a limited validated disease taxonomy;
- dry daylight operation with adequate visibility and supported wind.

### 17.2 Excluded from v1.0

PlantGuard UAV v1.0 excludes:

- custom airframe design;
- custom motors or ESCs;
- custom flight controller;
- custom low-level flight stabilization;
- crop spraying;
- pesticide recommendations;
- chemical dosage recommendations;
- definitive agronomic diagnosis;
- multispectral, thermal, hyperspectral, or LiDAR sensing;
- drone swarms;
- obstacle-avoidance research;
- fully unsupervised takeoff without operator approval;
- support for multiple simultaneous drones;
- support for multiple simultaneous field missions;
- automatic multi-flight field stitching;
- user-defined priority zones, guided routes, and custom route drafts;
- degraded-visibility, fog, mist, rain, or precipitation operation;
- multiple production crop taxonomies in the initial release;
- guaranteed classification of every PlantGuard disease class from high-altitude images;
- mobile-native application requirements;
- autonomous treatment actions.

## 18. User Acceptance Criteria

PlantGuard UAV v1.0 is acceptable from the farmer's perspective when:

1. A saved field can be selected through the application.
2. One connected drone can be prepared for the mission.
3. The system clearly reports whether takeoff is allowed.
4. Takeoff does not occur without farmer approval.
5. The drone surveys the planned inspectable area automatically and reports every skipped region.
6. Mission images are captured and associated with field locations.
7. The system distinguishes healthy and unhealthy observations.
8. Unhealthy observations are grouped into suspicious sites.
9. Revisit targets are generated without manual coordinate entry.
10. The drone captures lower-altitude images at selected sites.
11. The system returns likely disease predictions with confidence where evidence is sufficient.
12. The system identifies uncertain cases without forcing a prediction.
13. The drone returns home and lands.
14. The final field map shows where suspicious sites were found.
15. The farmer can review disease predictions, confidence, uncertainty, and supporting images.
16. The final mission report remains available after the mission ends.
17. Abort, return-home, and manual takeover remain available.

## 19. Product Definition of Done

PlantGuard UAV v1.0 is complete when all of the following are true:

- a saved field can be selected;
- one action starts the authorized workflow;
- unsafe or incomplete starts are rejected;
- the farmer approves every takeoff;
- the drone surveys at least the minimum accepted usable coverage of the planned inspectable area;
- geotagged RGB imagery is captured;
- healthy/unhealthy screening is performed;
- suspicious observations are grouped into sites;
- revisit targets are generated automatically;
- the drone captures lower-altitude revisit imagery;
- final disease predictions are produced where evidence is sufficient;
- confidence is shown;
- uncertain cases are reported honestly;
- the drone returns home and lands;
- the farmer receives an application-based field map and mission report;
- the workflow has been repeated across multiple missions;
- quantitative evaluation has been completed;
- important failure cases have been documented;
- manual takeover, abort, and return-home remain available;
- treatment recommendations remain outside the v1.0 product.

## 20. Future Product Extensions

Possible post-v1.0 extensions include:

- treatment-information integration reviewed by agronomic experts;
- additional crops;
- additional disease classes;
- multispectral or thermal sensing;
- onboard edge inference;
- improved real-time processing;
- optional companion-computer deployment;
- richer severity estimation;
- historical field comparison;
- multi-season analytics;
- cloud synchronization;
- mobile application;
- multi-drone support;
- obstacle-awareness integration;
- integration with farm-management systems.

These extensions shall not block PlantGuard UAV v1.0.

## 21. Requirement Traceability

Each major implementation task and test should reference one or more requirement identifiers from this document.

Examples:

```text
PR-MISSION-002
PR-SCREEN-001
PR-REVISIT-004
PR-CLASS-005
PR-DASH-009
PR-NFR-TRACE-003
```

A future requirements traceability matrix may map:

```text
requirement
→ implementation component
→ automated test
→ validation evidence
→ release status
```

## 22. Final Product Statement

PlantGuard UAV v1.0 is an operator-authorized autonomous RGB field-inspection system for one predefined agricultural field sector at a time, validated for one configured crop scope and dry daylight operation.

It surveys the planned inspectable area, reports excluded and unusable regions, performs healthy-versus-unhealthy screening, groups suspicious observations into physical inspection sites, revisits eligible sites at lower altitude, captures higher-detail images, attempts disease classification with confidence where image quality is sufficient, returns home, and presents the farmer with a georeferenced field-health map and diagnosis metrics through an application dashboard.

The system supports inspection and prioritization. It does not provide treatment recommendations or claim guaranteed agronomic diagnosis.
