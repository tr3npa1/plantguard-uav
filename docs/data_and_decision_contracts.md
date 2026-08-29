# PlantGuard UAV — Data and Decision Contracts

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Data and Decision Contracts |
| Target release | v1.0 |
| Status | Active |
| Related documents | `docs/product_requirements.md`, `docs/system_scope.md` |
| Last updated | 2026-07-16 |

## 1. Document Purpose

This document defines the data and decision contracts for PlantGuard UAV v1.0.

It specifies:

- the inputs required by the mission and perception system;
- the outputs produced by each processing stage;
- the decisions the system may make automatically;
- the decisions reserved for the farmer or operator;
- the healthy, unhealthy, uncertain, revisit, disease-classification, and manual-inspection logic;
- the confidence and uncertainty policy;
- the required farmer-facing report contents;
- the machine-readable artifacts retained for traceability and evaluation;
- the minimum evidence that must accompany every final result.

The document does not define low-level flight-control algorithms or final numerical confidence thresholds. Those values shall be calibrated later from validation data and stored in versioned configuration.

## 2. Contract Principles

All PlantGuard UAV data and decisions shall follow these principles.

### 2.1 Traceability

Every result must be traceable to:

```text
field
mission
source image
observation
suspicious site
revisit image
model
model version
configuration
timestamp
```

### 2.2 Explicit Uncertainty

The system shall not force a healthy, unhealthy, or disease result when the available evidence is insufficient.

Uncertain outcomes must be represented explicitly.

### 2.3 Evidence Preservation

Every suspicious or final disease result must preserve the supporting image evidence and relevant metadata.

### 2.4 Human Override

The system shall never override:

```text
operator abort
operator return-to-home
manual takeover
```

### 2.5 Conservative Revisit Policy

High-confidence unhealthy observations and uncertain survey observations shall be revisited whenever mission safety, route validity, battery reserve, weather, and hardware health permit.

### 2.6 Separation of Screening and Diagnosis

The initial survey stage performs:

```text
healthy / unhealthy / uncertain screening
```

The revisit stage performs:

```text
health reassessment
+
disease classification when unhealthy
```

The initial survey shall not claim a final disease diagnosis.

## 3. Core Entity Model

PlantGuard UAV v1.0 uses the following core entities.

### 3.1 Field

A saved agricultural area containing one or more operator-defined sectors. One mission selects exactly one sector.

Minimum fields:

```text
field_id
field_name
boundary
sector_id
sector_boundary
home_location
crop_type
exclusion_zones
survey_configuration
revisit_configuration
```

### 3.2 Mission

One operator-authorized inspection of one field sector using one drone.

Minimum fields:

```text
mission_id
field_id
sector_id
drone_id
workflow_state
mission_activity
vehicle_state_snapshot
started_at
completed_at
operator_authorized_at
configuration_version
software_version
```

### 3.3 Image Capture

One image and its capture context.

Minimum fields:

```text
image_id
mission_id
capture_stage
file_path
captured_at
captured_monotonic_ns
longitude_deg
latitude_deg
altitude_agl_m
altitude_amsl_m
horizontal_uncertainty_m
vertical_uncertainty_m
coordinate_reference
altitude_reference
time_sync_reference
vehicle_attitude
camera_metadata
quality_status
```

### 3.4 Survey Observation

One health-screening result associated with a visible crop region, plant, canopy region, or image tile.

Minimum fields:

```text
observation_id
mission_id
image_id
region
geographic_location
health_status
health_confidence
quality_status
screening_model_version
```

### 3.5 Suspicious Site

One physical location formed from one or more unhealthy or uncertain survey observations.

Minimum fields:

```text
site_id
mission_id
supporting_observation_ids
representative_location
survey_health_status
site_priority
revisit_required
revisit_status
```

### 3.6 Revisit Capture

One higher-detail image captured for a suspicious site.

Minimum fields:

```text
revisit_image_id
mission_id
site_id
file_path
captured_at
captured_monotonic_ns
longitude_deg
latitude_deg
altitude_agl_m
altitude_amsl_m
coordinate_reference
altitude_reference
time_sync_reference
quality_status
```

### 3.7 Final Site Result

The final health and disease result for one suspicious site.

Minimum fields:

```text
site_id
final_status
final_health_status
health_confidence
predicted_disease
disease_confidence
manual_inspection_recommended
reason_codes
supporting_revisit_image_ids
model_versions
```

## 4. Mission Inputs

### 4.1 Farmer and Operator Inputs

Normal farmer interaction shall require only:

- selection of one saved field;
- operator approval before takeoff;
- optional pause;
- optional abort;
- optional return-to-home;
- optional manual takeover;
- later deletion or retention decisions for mission data.

The farmer shall not normally enter:

- neural-network thresholds;
- image-overlap percentages;
- route-planning internals;
- model preprocessing values;
- raw geographic calculations;
- model file paths.

Those values belong in validated, versioned configuration.

### 4.2 Field Inputs

The selected field configuration shall contain:

```text
field_id
sector_id
field_name
crop_type
field boundary polygon
sector boundary polygon
home or takeoff location
exclusion zones
survey altitude AGL
survey speed
front overlap
side overlap
revisit altitude AGL
revisit speed
production environment: nominal_dry_daylight
battery policy
```

### 4.3 Drone and Telemetry Inputs

The mission system may consume:

```text
vehicle connection status
armed state
flight mode
longitude_deg
latitude_deg
altitude_agl_m
altitude_amsl_m
ground speed
vehicle attitude
battery percentage
estimated remaining flight time
GPS health
home position
mission progress
flight-controller health
return-to-home availability
```

### 4.4 Camera Inputs

The image system may consume:

```text
RGB image
capture timestamp
camera identifier
image dimensions
focal information when available
camera orientation
capture confirmation
storage status
lens or image-obscuration status
```

### 4.5 Weather and Safety Inputs

The mission system may consume:

```text
operator weather confirmation
configured operating mode
wind estimate or measurement
visibility status
precipitation status
hardware weather rating
image-quality trend
route safety status
```

### 4.6 Model Inputs

The perception system shall load:

```text
screening model
screening model metadata
disease-classification model
disease-classification metadata
image-quality thresholds
confidence policy
supported crop and disease labels
model version
configuration version
```

## 5. Mission Output Structure

A completed or partially completed mission should produce the following local structure:

```text
results/<mission_id>/
├── manifests/
│   ├── mission_manifest.csv
│   ├── accepted_images.csv
│   ├── rejected_images.csv
│   └── capture_events.csv
├── perception/
│   ├── screening_predictions.csv
│   ├── suspicious_sites.csv
│   ├── revisit_targets.csv
│   ├── revisit_predictions.csv
│   └── final_site_results.csv
├── maps/
│   ├── field_boundary.geojson
│   ├── flight_path.geojson
│   ├── survey_observations.geojson
│   ├── suspicious_sites.geojson
│   └── field_map.html
├── evidence/
│   ├── survey/
│   └── revisits/
├── configuration/
│   ├── mission_config.yaml
│   ├── model_metadata.json
│   └── software_version.json
├── logs/
│   ├── mission_events.jsonl
│   └── errors.jsonl
├── mission_summary.json
└── report.html
```

A mission that is aborted or fails shall still preserve every valid artifact produced before termination.

## 6. Standard Status Values

### 6.1 Mission State Dimensions

The following dimensions are persisted separately. A processing job may run while the mission activity is `return_home` or `landing`; no job state changes physical flight.

#### Mission Workflow State

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

#### Mission Activity

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

#### Vehicle Operational State

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

#### Processing Job State

```text
queued
running
retry_wait
paused
succeeded
failed
cancelled
```

### 6.2 Image Quality Status

```text
accepted
rejected_blur
rejected_underexposure
rejected_overexposure
rejected_obstruction
rejected_low_plant_visibility
rejected_corrupt
rejected_missing_metadata
rejected_other
```

### 6.3 Survey Health Status

```text
healthy
unhealthy
uncertain
not_evaluated
```

### 6.4 Revisit Status

```text
not_required
planned
in_progress
completed
skipped_safety
skipped_battery
skipped_route_invalid
skipped_weather
capture_failed
not_completed
```

### 6.5 Final Site Status

```text
healthy
healthy_after_suspicious_survey
unhealthy_disease_identified
unhealthy_disease_uncertain
health_status_unresolved
manual_inspection_recommended
revisit_not_completed
```

`revisit_capture_failed` is not a final site status. It is a reason code attached to `revisit_not_completed`.

For production metrics:

- `healthy_after_suspicious_survey` and `unhealthy_disease_identified` count as automatically resolved suspicious-site outcomes;
- `unhealthy_disease_uncertain`, `health_status_unresolved`, `manual_inspection_recommended`, and `revisit_not_completed` remain explicit outcomes requiring uncertainty or manual-action reporting and do not count as automatic resolution.

## 7. Survey Screening Contract

Each accepted crop observation shall be processed by the healthy/unhealthy screening stage.

The stage shall produce:

```json
{
  "observation_id": "obs_000001",
  "mission_id": "mission_000001",
  "image_id": "image_000125",
  "health_status": "healthy",
  "health_confidence": 0.93,
  "quality_status": "accepted",
  "screening_model_version": "screening_model_v1",
  "created_at": "ISO-8601 timestamp"
}
```

The exact confidence thresholds are not fixed in this document.

They shall be:

- model-specific;
- selected using validation data;
- stored in versioned configuration;
- separate from dashboard code;
- auditable in the final mission record.

## 8. Authoritative Survey-to-Revisit Decision Logic

### 8.1 High-Confidence Healthy

When the survey model returns high-confidence healthy:

```text
record observation as healthy
→ do not create a suspicious site from that observation
→ do not require revisit solely because of that observation
```

Required result:

```json
{
  "health_status": "healthy",
  "revisit_required": false,
  "final_status": "healthy"
}
```

A healthy result may later support field-level health metrics.

### 8.2 High-Confidence Unhealthy

When the survey model returns high-confidence unhealthy:

```text
create a suspicious observation
→ create or support a suspicious site
→ mark revisit as required
→ revisit to identify disease type
```

The site shall be included in the revisit plan unless one of the following prevents it:

```text
flight safety
battery reserve
route validity
weather
vehicle health
camera failure
operator abort
```

If revisit cannot be completed, the site shall remain in the report as:

```text
revisit_not_completed
manual_inspection_recommended
```

### 8.3 Uncertain Survey Result

When the survey model returns uncertain:

```text
preserve the observation
→ treat it conservatively as a suspicious candidate
→ create or support a suspicious site
→ always attempt revisit
→ reassess both health and disease status
```

“Always attempt revisit” means the site is included in revisit planning unless safety or mission constraints make the revisit impossible.

An uncertain observation must not be silently converted to healthy.

## 9. Revisit Decision Contract

The revisit stage shall capture higher-detail RGB imagery for each reachable suspicious site.

The revisit system shall:

1. navigate to the planned site;
2. stabilize the drone;
3. capture one or more images;
4. validate image quality;
5. retry capture when permitted and useful;
6. reassess health status;
7. perform disease classification when the site is unhealthy;
8. preserve every accepted and rejected revisit image;
9. produce a final site result or manual-inspection outcome.

## 10. Final Decision Logic After Revisit

### 10.1 Survey Result Was High-Confidence Unhealthy

#### Case A — Unhealthy Confirmed and Disease Identified

```text
unhealthy high confidence
+
one disease high confidence
→ return disease and confidence
```

Final status:

```text
unhealthy_disease_identified
```

Example:

```json
{
  "site_id": "site_0042",
  "final_status": "unhealthy_disease_identified",
  "final_health_status": "unhealthy",
  "health_confidence": 0.96,
  "predicted_disease": "Tomato___Late_blight",
  "disease_confidence": 0.91,
  "manual_inspection_recommended": false
}
```

#### Case B — Unhealthy Confirmed but Disease Uncertain

```text
unhealthy high confidence
+
disease low confidence or inconsistent
→ return unhealthy
→ do not force disease label
→ recommend manual inspection
```

Final status:

```text
unhealthy_disease_uncertain
```

Example:

```json
{
  "site_id": "site_0043",
  "final_status": "unhealthy_disease_uncertain",
  "final_health_status": "unhealthy",
  "health_confidence": 0.94,
  "predicted_disease": null,
  "disease_confidence": null,
  "manual_inspection_recommended": true,
  "reason_codes": [
    "disease_classification_uncertain"
  ]
}
```

#### Case C — Revisit Evidence Is Unusable

```text
revisit image unusable or insufficient
→ do not force health or disease result
→ recommend manual inspection
```

### 10.2 Survey Result Was Uncertain

#### Case A — Unhealthy Confirmed and Disease Identified

```text
unhealthy high confidence
+
one disease high confidence
→ return disease and confidence
```

Final status:

```text
unhealthy_disease_identified
```

#### Case B — Unhealthy Confirmed but Disease Uncertain

```text
unhealthy high confidence
+
disease low confidence or inconsistent
→ return unhealthy
→ recommend manual inspection
```

Final status:

```text
unhealthy_disease_uncertain
```

#### Case C — Healthy Confirmed After Suspicious Survey

```text
healthy high confidence after revisit
→ return healthy
→ retain caution that survey appearance was abnormal
→ suggest optional manual inspection
```

Final status:

```text
healthy_after_suspicious_survey
```

Example:

```json
{
  "site_id": "site_0044",
  "final_status": "healthy_after_suspicious_survey",
  "final_health_status": "healthy",
  "health_confidence": 0.92,
  "predicted_disease": null,
  "disease_confidence": null,
  "manual_inspection_recommended": false,
  "advisory": "The initial survey appearance was abnormal. Optional manual inspection is suggested."
}
```

The site shall remain visible on the final field map because it was suspicious during the initial survey.

#### Case D — Health Status Remains Uncertain

```text
health status remains uncertain
→ do not force healthy or unhealthy
→ recommend manual inspection
```

Final status:

```text
health_status_unresolved
```

#### Case E — Revisit Cannot Be Completed

```text
revisit impossible due to safety, battery, route, weather, or hardware failure
→ preserve site
→ report reason
→ recommend manual inspection
```

Final status:

```text
revisit_not_completed
```

## 11. Multiple Revisit Image Aggregation

A suspicious site may produce multiple accepted revisit images.

The aggregation procedure shall:

1. reject unusable images;
2. run health reassessment on every accepted image;
3. run disease classification on every accepted image classified as unhealthy;
4. preserve individual predictions;
5. calculate image-quality-aware agreement;
6. produce one final site result only when evidence is sufficiently consistent;
7. withhold the final disease label when views conflict materially.

The site record shall preserve:

```text
images captured
images accepted
images rejected
individual health predictions
individual disease predictions
quality scores
agreement score
aggregated health result
aggregated disease result
final confidence
```

The exact aggregation formula shall be defined during model validation.

## 12. Confidence Policy

### 12.1 General Rules

Confidence thresholds shall:

- be model-specific;
- be calibrated from validation data;
- be stored in versioned configuration;
- be included in mission metadata;
- not be hard-coded into farmer-facing interface code;
- support different crops or model versions when required.

### 12.2 Screening Threshold Configuration

A screening configuration may later define:

```text
healthy confidence threshold
unhealthy confidence threshold
uncertain interval
minimum image-quality score
```

Illustrative example only:

```text
healthy probability >= configured threshold
→ healthy

unhealthy probability >= configured threshold
→ unhealthy

neither requirement is met
→ uncertain
```

No illustrative number in this document is a release threshold.

### 12.3 Disease Threshold Configuration

A disease-classification configuration may later define:

```text
minimum top-1 confidence
minimum top-1 versus top-2 margin
minimum view agreement
minimum accepted-image count
minimum image-quality score
supported-class policy
```

## 13. Standard Reason Codes

The following reason codes shall be used where applicable:

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

Every withheld result shall contain:

```text
machine-readable reason code
human-readable explanation
supporting evidence where available
timestamp
stage that produced the outcome
```

## 14. Automated Decisions

PlantGuard UAV may automatically decide:

- whether mission input is structurally valid;
- whether an image is usable;
- whether an observation is healthy, unhealthy, or uncertain;
- whether observations belong to the same physical site;
- whether a suspicious site requires revisit;
- how suspicious sites are prioritized;
- whether battery and route constraints allow revisit;
- whether a revisit image is usable;
- whether a revisit confirms healthy or unhealthy;
- which disease is most likely;
- whether disease evidence is sufficient;
- whether manual inspection is recommended;
- whether processing can resume from saved outputs.

An automated revisit may proceed after the original operator-authorized mission begins, provided:

- preflight approval was granted;
- route validation passes;
- battery reserve remains sufficient;
- weather remains supported;
- vehicle health remains acceptable;
- no abort or return-home command has been issued.

## 15. Human-Controlled Decisions

The farmer or operator retains control over:

- selecting the field;
- approving takeoff;
- pausing the mission;
- aborting the mission;
- commanding return-to-home;
- taking manual control;
- deciding whether to act on a model result;
- obtaining expert agronomic confirmation;
- deciding whether and how to treat the crop;
- deleting or retaining mission data.

The system shall not:

- prescribe treatment in v1.0;
- override abort;
- override return-to-home;
- block manual takeover;
- represent uncertain output as guaranteed diagnosis.

## 16. Farmer-Facing Dashboard Contract

### 16.1 Mission Summary View

The dashboard shall display:

```text
mission status
field name
mission duration
area or coverage processed
images captured
images accepted
images rejected
survey completion
revisit completion
return-home status
```

### 16.2 Field-Health Summary View

The dashboard shall display:

```text
healthy observations or regions
unhealthy observations or regions
uncertain observations or regions
healthy percentage
unhealthy percentage
uncertain percentage
```

These values describe observed regions or resolved individual plants.

The application shall not describe them as the exact percentage of all plants unless individual-plant detection and counting have been validated.

### 16.3 Disease Summary View

The dashboard shall display:

```text
identified diseases
number of sites per disease
confidence distribution
unhealthy sites with uncertain disease
manual-inspection cases
revisit failures
```

### 16.4 Interactive Field Map

Each suspicious-site marker should expose:

```text
site ID
location
initial survey result
survey confidence
survey image preview
revisit status
revisit image preview
final health status
predicted disease
disease confidence
advisory
manual-inspection recommendation
reason codes
```

Sites finalized as `healthy_after_suspicious_survey` shall remain visible with a cautionary marker.

### 16.5 Farmer-Facing Language

The dashboard shall prefer phrases such as:

```text
Likely disease
Confidence
Unhealthy — disease uncertain
Manual inspection recommended
Healthy after closer inspection
Initial survey looked abnormal
```

It shall avoid phrases such as:

```text
Guaranteed diagnosis
Definitely disease-free
Treatment required
Apply pesticide
```

## 17. Machine-Readable Output Contracts

### 17.1 Mission Summary

`mission_summary.json` shall include:

```text
mission identity
field identity
mission status
timing
coverage metrics
capture metrics
screening metrics
site metrics
revisit metrics
classification metrics
error summary
model versions
software version
configuration version
```

### 17.2 Screening Predictions

`screening_predictions.csv` shall include at minimum:

```text
observation_id
mission_id
image_id
region coordinates
longitude_deg
latitude_deg
coordinate_reference
horizontal_uncertainty_m
health_status
health_confidence
quality_status
screening_model_version
timestamp
```

### 17.3 Suspicious Sites

`suspicious_sites.csv` shall include at minimum:

```text
site_id
mission_id
representative_latitude
representative_longitude
supporting_observation_count
survey_health_status
site_priority
revisit_required
revisit_status
```

### 17.4 Final Site Results

`final_site_results.csv` shall include at minimum:

```text
site_id
mission_id
final_status
final_health_status
health_confidence
predicted_disease
disease_confidence
manual_inspection_recommended
reason_codes
accepted_revisit_image_count
rejected_revisit_image_count
screening_model_version
classification_model_version
timestamp
```

### 17.5 Geographic Outputs

GeoJSON shall be generated for:

```text
field boundary
survey flight path
survey observations
suspicious sites
revisit targets
final site results
```

The production geospatial and time contract is:

- persisted GeoJSON uses WGS 84 / EPSG:4326;
- GeoJSON positions use `[longitude, latitude]` axis order in decimal degrees;
- metric distance, area, clustering, and coverage calculations use a mission-selected local projected CRS recorded in mission metadata;
- local projected coordinates use easting/x and northing/y in metres;
- `altitude_agl_m` is required for flight and capture geometry and records its source;
- `altitude_amsl_m` may also be retained when available but shall never be substituted silently for AGL;
- every pose records coordinate reference, altitude reference, vehicle/camera frame identifiers, and available uncertainty;
- persisted wall-clock timestamps use UTC RFC 3339/ISO 8601;
- capture correlation also retains a monotonic timestamp and the PX4-to-ground clock-mapping reference;
- telemetry interpolation tolerance is versioned configuration validated against the selected hardware;
- an image outside the qualified synchronization or pose-uncertainty limit is rejected for geospatial decisions rather than assigned a guessed position.

## 18. Data Retention Policy

### 18.1 Default v1.0 Policy

Raw mission images shall be retained by default.

Reasons include:

- debugging;
- model reprocessing;
- ground-truth review;
- failure analysis;
- model improvement;
- research evidence;
- reproducibility.

The operator may delete mission images after reviewing the mission.

### 18.2 Derived Artifacts

The following shall remain unless explicitly deleted:

```text
mission metadata
predictions
site records
maps
reports
logs
configuration snapshot
model metadata
```

### 18.3 Future Retention Modes

A later product version may support:

```text
retain indefinitely
retain for configured number of days
delete raw images after report generation
manual deletion only
archive externally
```

## 19. Decision Audit Requirements

For every final site result, the system shall be able to answer:

1. Which survey images created the observation?
2. Why was the site considered suspicious?
3. Why was it selected for revisit?
4. Was the revisit completed?
5. Which revisit images were accepted or rejected?
6. What health predictions were produced?
7. What disease predictions were produced?
8. Which thresholds and model versions were used?
9. Why was the final label returned or withheld?
10. Why was manual inspection recommended?

## 20. Data-Contract Acceptance Criteria

The data and decision contract baseline is complete when:

- all required mission inputs are defined;
- all required outputs are defined;
- core entities are defined;
- status values are standardized;
- workflow, mission activity, vehicle, and processing-job states are separated;
- coordinate, altitude, frame, and timestamp conventions are explicit;
- healthy, unhealthy, and uncertain survey handling is explicit;
- high-confidence unhealthy observations require revisit;
- uncertain survey observations require attempted revisit;
- post-revisit health and disease outcomes are explicit;
- healthy-after-suspicious-survey behavior is explicit;
- manual-inspection fallbacks are explicit;
- exact thresholds are deferred to validation and versioned configuration;
- farmer-facing dashboard contents are defined;
- machine-readable artifacts are defined;
- raw image retention behavior is defined;
- every final result is traceable to evidence, model, and configuration.

## 21. Final Decision Statement

PlantGuard UAV v1.0 uses a two-stage perception and revisit policy.

During the planned-inspectable-area survey:

```text
high-confidence healthy
→ record as healthy
→ no revisit required

high-confidence unhealthy
→ create or support suspicious site
→ always attempt revisit

uncertain
→ create or support suspicious site
→ always attempt revisit
```

After revisit:

```text
unhealthy high confidence
+
disease high confidence
→ return disease and confidence

unhealthy high confidence
+
disease uncertain
→ return unhealthy
→ recommend manual inspection

healthy high confidence after uncertain survey
→ return healthy
→ retain caution
→ suggest optional manual inspection

health remains uncertain
→ recommend manual inspection

revisit cannot be completed
→ preserve site and reason
→ recommend manual inspection
```

No safety, battery, route, weather, hardware, or operator constraint may be ignored solely to satisfy the revisit policy.
