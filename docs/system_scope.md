# PlantGuard UAV — System Scope

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | System Scope |
| Target release | v1.0 |
| Status | Active |
| Primary operating model | One predefined field and one drone at a time |
| Primary sensor | High-resolution RGB camera |
| Last updated | 2026-07-16 |

## 1. Document Purpose

This document defines the technical and operational scope of PlantGuard UAV v1.0.

It establishes:

- the environments in which the system is expected to operate;
- the crop, field, sensor, and flight assumptions;
- the provisional operating envelope;
- the supported weather modes;
- the conditions that must block mission start;
- the relationship between nominal operation and degraded-weather adaptation;
- the boundaries between supported behavior and future extensions.

The product-level user experience and functional requirements are defined separately in `docs/product_requirements.md`.

## 2. Version 1.0 Scope Summary

PlantGuard UAV v1.0 is an operator-authorized autonomous RGB field-inspection system.

It supports:

- one predefined agricultural field sector at a time;
- one programmable drone at a time;
- a previously saved field boundary;
- automatic planned-inspectable-area survey planning;
- RGB image capture and geotagging;
- healthy-versus-unhealthy screening;
- suspicious-site grouping;
- automatic lower-altitude revisit planning;
- revisit image capture;
- disease classification with confidence where image quality is sufficient;
- automatic return-to-home and landing;
- farmer-facing results through an application dashboard.

The production v1.0 release is validated for one configured crop or crop family, a limited supported disease taxonomy, and dry daylight operation only.

The system is designed for open agricultural fields. It does not depend on research-grade obstacle avoidance and does not perform crop treatment.

## 3. Supported Operating Environment

### 3.1 Primary Environment

The primary v1.0 operating environment is:

```text
Open agricultural field
Predefined field boundary
Known takeoff and home area
Daylight operation
One drone
One active mission
RGB imaging
Operator present and able to intervene
```

### 3.2 Field Type

The intended field is:

- geographically bounded before the mission;
- sufficiently open for planned waypoint flight;
- free from unmapped structures along the route;
- suitable for visual observation by the operator;
- accessible for later ground-truth inspection where required.

### 3.3 Production Operating Mode

PlantGuard UAV v1.0 supports one production environmental mode:

```text
nominal_dry_daylight
```

Required conditions include dry weather, adequate daylight and visibility, supported wind, stable imaging, no precipitation, and no significant condensation risk.

Fog, mist, rain, precipitation, night operation, and degraded-visibility flight are outside the production v1.0 operating envelope. Detection of those conditions before takeoff blocks the mission; detection in flight causes the Safety Supervisor to select return-home or controlled landing. Supporting an additional environmental mode requires formal product change control, hardware qualification, safety analysis, and new field acceptance evidence.

## 4. Crop Assumptions

### 4.1 Software Crop Scope

The software architecture shall remain extensible to multiple crops.

The field, mission, dataset, model, and reporting schemas shall not be hard-coded to one crop.

### 4.2 First Real-World Validation Scope

The production v1.0 release shall be qualified for one configured crop or crop family and a limited, versioned disease taxonomy.

The crop shall be selected according to:

- reliable field access;
- availability of healthy and unhealthy examples;
- availability of reviewed or confirmed disease labels;
- suitability for aerial observation;
- compatibility with PlantGuard's existing disease classes;
- ability to perform ground inspection after the mission.

The exact crop may remain `TBD` until field access and data-collection arrangements are confirmed.

### 4.3 High-Altitude Disease Claims

The wide survey stage shall not attempt to classify every PlantGuard disease directly from high-altitude images.

The wide survey is responsible for:

```text
healthy-versus-unhealthy screening
suspicious-region localization
revisit-target generation
```

Specific disease classification is performed using lower-altitude revisit imagery when visual evidence is sufficient.

### 4.4 Individual-Plant Identification

The planned inspectable area of the selected field sector shall be surveyed.

However, v1.0 shall claim individual-plant identification only when:

- crop spacing makes plants visually separable;
- camera resolution is sufficient;
- altitude and image quality are suitable;
- plant overlap does not make individual identity unreliable.

Where individual plants cannot be resolved reliably, the system shall operate on:

- canopy regions;
- crop-row sections;
- crop clusters;
- suspicious patches.

## 5. Sensor Assumptions

### 5.1 Primary Sensor

PlantGuard UAV v1.0 shall use a high-resolution RGB camera.

The camera system should support:

- still-image capture;
- capture timestamps;
- stable mounting;
- sufficient image resolution;
- known image dimensions;
- known or discoverable camera parameters;
- reliable storage;
- location association through telemetry or metadata.

### 5.2 Camera Orientation

The nominal survey camera orientation is downward-facing or nadir.

During revisit, the system may use:

- downward-facing capture;
- a slight camera angle;
- multiple viewpoints;
- short hover-based image sequences.

The selected orientation must not compromise flight safety.

### 5.3 Excluded Sensors

The following are outside v1.0:

- multispectral cameras;
- hyperspectral cameras;
- thermal cameras;
- LiDAR;
- radar;
- active depth cameras.

The architecture may allow these sensors in later releases, but they are not required for v1.0 completion.

### 5.4 Sensor Health

The mission must not start when:

- the camera is unavailable;
- storage is insufficient;
- image capture cannot be confirmed;
- required metadata cannot be recorded;
- the lens is visibly obscured;
- condensation or water droplets make useful imagery unlikely;
- camera or gimbal health checks fail.

## 6. Field Assumptions

PlantGuard UAV v1.0 assumes:

- one contiguous predefined field;
- one field boundary loaded before mission planning;
- one known takeoff and home location;
- one active mission at a time;
- open agricultural terrain;
- no intended flight beneath trees, wires, roofs, or structures;
- obstacles and restricted areas are mapped or excluded before flight;
- the operator remains close enough to supervise the mission;
- the route remains inside the approved boundary and geofence;
- the selected altitude provides safe clearance over crops and known obstacles.

### 6.1 Exclusion Zones

The field configuration may contain exclusion zones for:

- trees;
- poles;
- power lines;
- buildings;
- irrigation equipment;
- ponds or water bodies;
- people or livestock areas;
- restricted airspace;
- unsafe terrain.

The route planner must not generate normal survey or revisit waypoints inside an exclusion zone.

### 6.2 Obstacle-Avoidance Scope

Research-grade autonomous obstacle avoidance is not required for v1.0.

PlantGuard UAV relies on:

- predefined field boundaries;
- mapped exclusion zones;
- conservative altitude;
- operator supervision;
- drone-native safety features where available;
- mission validation before takeoff.

Unknown or uncertain obstacle conditions must block mission approval.

## 7. Flight Assumptions

All values in this section are provisional until the drone, camera, field, and legal operating limits are finalized.

The final configured limit must always use the most restrictive applicable constraint among:

```text
manufacturer limit
project safety limit
legal limit
field-specific limit
operator judgement
```

### 7.1 Nominal Survey Flight

| Parameter | Provisional value |
|---|---:|
| Survey altitude | 20–30 m above ground level |
| Survey speed | 2–4 m/s |
| Camera orientation | Nadir/downward-facing |
| Front overlap | 75% |
| Side overlap | 65% |
| Planned usable battery consumption | Maximum 70% |
| Minimum planned reserve | 30% |

The nominal survey is intended to:

- cover the planned inspectable area;
- provide repeated visual coverage;
- collect sufficient imagery for health screening;
- support approximate geospatial localization;
- retain enough battery for safe return and unexpected delay.

### 7.2 Nominal Revisit Flight

| Parameter | Provisional value |
|---|---:|
| Revisit altitude | 5–10 m above crop canopy |
| Speed near target | 1–2 m/s |
| Capture behavior | Stabilize, capture one or more images |
| Camera orientation | Downward or slightly angled |
| Site handling | Predict, reject, retry, or flag |

The revisit stage is intended to:

- capture higher-detail imagery;
- verify unhealthy status;
- provide disease-classification evidence;
- support uncertainty handling;
- retain precise site traceability.

### 7.3 Image Overlap

The provisional nominal overlap is:

```text
Front overlap: 75%
Side overlap: 65%
```

Overlap may be changed only through validated mission configuration and route revalidation.

The overlap policy supports:

- reducing coverage gaps;
- replacing unusable frames;
- viewing the same site more than once;
- geospatial aggregation;
- duplicate-site analysis;
- improved confidence in suspicious-site formation.

### 7.4 Battery Policy

Normal mission planning shall use no more than approximately 70% of estimated usable battery capacity.

At least 30% shall remain reserved for:

- return-to-home;
- landing;
- wind variation;
- navigation delay;
- failed image captures;
- route changes;
- battery-estimation error;
- emergency handling.

A revisit mission shall not begin or continue unless estimated remaining energy is sufficient for:

```text
planned revisit activity
+
return-to-home
+
landing
+
required reserve
```

The v1.0 mission boundary is one field sector that fits the validated survey, same-flight decision, revisit, return, landing, and reserve envelope. A larger field must be divided into separately approved sectors and independent missions. Automatic multi-flight stitching is excluded from v1.0.

### 7.5 Provisional Wind Envelope

The initial project-level planning thresholds are:

| Condition | Provisional threshold |
|---|---:|
| Sustained wind | Approximately 5 m/s maximum |
| Gusts | Approximately 7 m/s maximum |

These thresholds are not permission to exceed the selected aircraft's limits.

The final configured threshold shall be reduced when required by:

- manufacturer limits;
- aircraft payload;
- battery condition;
- field geometry;
- precipitation;
- visibility;
- operator experience;
- local rules.

PX4 or the selected flight stack may provide wind warnings or failsafe behavior, but the project shall not rely on software estimation as the only weather check.

## 8. Environmental Constraints

### 8.1 Daylight

V1.0 is restricted to daylight operation with adequate and stable illumination.

The system should avoid:

- night operation;
- very low illumination;
- severe glare;
- rapidly changing light;
- heavy haze that removes useful image contrast;
- conditions in which the operator cannot supervise the drone.

### 8.2 Rain and Precipitation

Rain and precipitation are unsupported in production v1.0. Any detected precipitation before takeoff is a hard blocker. Any detected precipitation in flight requires a conservative return-home or controlled-landing decision. Reducing altitude, speed, or route length does not make precipitation operation supported.

### 8.3 Fog and Mist

Fog and mist are unsupported in production v1.0 because they can invalidate visual supervision, obstacle awareness, and image-quality assumptions. Their presence blocks mission start or triggers return-home or controlled landing.

### 8.4 Condensation

Condensation may affect:

- camera lens;
- gimbal;
- electronics;
- connectors;
- companion computer;
- payload enclosure.

Preflight checks shall look for visible condensation or lens fogging.

When condensation is detected:

- image capture shall be tested;
- the mission shall be delayed or blocked;
- the system shall not assume that lower altitude will correct the issue.

### 8.5 Environmental Monitoring

Weather acceptance is not a one-time preflight decision.

During the mission, the system should monitor available indicators such as:

- operator weather confirmation;
- measured or configured wind;
- camera image quality;
- GPS health;
- vehicle stability;
- precipitation indication when available;
- visibility-related operator input;
- repeated image rejection;
- lens-obscuration detection.

A mission may begin only in `nominal_dry_daylight` and shall transition toward return-home or controlled landing if the production envelope is no longer maintained.

## 9. Runtime Environmental Degradation Response

Environmental degradation never expands the approved operating envelope. When daylight, visibility, wind, dryness, image quality, or operator supervision leaves the qualified range:

1. no new survey or revisit work is started;
2. the condition and available evidence are recorded;
3. the Safety Supervisor chooses return-home or controlled landing;
4. PX4 native failsafes and manual control remain authoritative;
5. partial mission evidence and uninspected regions remain visible.

Mission parameters shall not be modified merely to continue unsupported weather operation.

## 10. Provisional Production Operating Envelope

| Area | Production v1.0 envelope |
|---|---|
| Weather | Dry; no precipitation |
| Lighting | Daylight with adequate, stable illumination |
| Visibility | Clear, adequate for VLOS and useful imaging |
| Wind | Within the configured limit and the selected platform's stricter limit |
| Survey altitude | 20–30 m AGL provisional |
| Survey speed | 2–4 m/s provisional |
| Image overlap | 75% front / 65% side provisional |
| Battery reserve | At least 30% provisional |
| Mission continuation | Only while every qualified condition remains satisfied |
| Envelope violation | Block start or return/land safely |

All numerical values remain provisional until the exact platform, camera, crop, field sector, and applicable operating limits are qualified.

## 11. Mission-Start Refusal Conditions

The system shall refuse mission start when any blocking condition is present.

### 11.1 Field and Route

- missing field boundary;
- invalid field geometry;
- missing home location;
- route outside approved boundary;
- route intersects an exclusion zone;
- unresolved obstacle risk;
- required geofence unavailable;
- route cannot be completed with required battery reserve.

### 11.2 Drone and Flight Controller

- drone unavailable;
- flight controller unhealthy;
- required calibration incomplete;
- GPS or positioning quality inadequate;
- home position unavailable;
- battery below configured threshold;
- telemetry link unavailable;
- return-to-home configuration invalid.

### 11.3 Camera and Computing

- camera unavailable;
- image capture fails;
- storage insufficient;
- lens obscured;
- condensation present;
- required model unavailable;
- required configuration invalid;
- mission software unhealthy;
- onboard or ground-station processing unavailable when required.

### 11.4 Weather and Visibility

- wind above configured threshold;
- rain without approved weather-rated hardware;
- precipitation above approved hardware limit;
- fog prevents visual line of sight;
- visibility is insufficient for route safety;
- image-quality test fails;
- severe glare or darkness prevents useful capture;
- operator judges conditions unsafe.

### 11.5 Human Authorization

- operator approval not provided;
- operator unable to supervise;
- manual takeover mechanism unavailable;
- return-to-home control unavailable.

## 12. Runtime Termination and Return Conditions

The system shall initiate an abort, return-to-home, or safe landing response when required by:

- battery reserve threshold;
- flight-controller health failure;
- GPS degradation;
- telemetry loss;
- unexpected route deviation;
- visibility degradation;
- precipitation increase;
- repeated image-quality failure;
- camera failure;
- unsafe wind;
- operator abort;
- operator return-home command;
- companion-computer failure when continued flight is unsafe;
- inability to complete revisit plus safe return.

The final action depends on the active flight-controller failsafe policy and the safest available response.

## 13. Supported Processing Architecture

V1.0 may use either:

### 13.1 Ground-Station Processing

The drone captures and transfers images while a ground computer performs:

- image validation;
- tiling;
- screening;
- site grouping;
- revisit planning;
- disease classification;
- mapping;
- reporting.

### 13.2 Post-Flight Processing

The first survey may be processed after landing during early development and validation.

This remains acceptable for intermediate milestones but does not satisfy the final automatic in-mission revisit workflow.

### 13.3 Companion-Computer Processing

Ground-station-first is the default production topology. A companion computer is promoted into the v1.0 deployment only if measured image-transfer and inference timing cannot produce a safe same-flight revisit decision within the validated energy budget.

Full disease classification may still occur on:

- the companion computer;
- a ground station;
- a hybrid system.

The product requirement is correct autonomous behavior, not that every model must execute onboard. Post-flight-only processing does not satisfy the mandatory same-flight revisit workflow. If neither the ground path nor a qualified companion path passes the timing gate, production release is blocked.

## 14. Included in Version 1.0

Version 1.0 includes:

- ready-made programmable drone;
- RGB camera;
- one field and one drone at a time;
- one field sector per mission;
- predefined field boundary;
- operator-approved takeoff;
- automatic survey;
- geotagged image collection;
- healthy/unhealthy screening;
- suspicious-site grouping;
- revisit planning;
- lower-altitude revisit;
- final disease classification with confidence;
- uncertainty handling;
- return-to-home and landing;
- farmer dashboard;
- field map;
- final report;
- nominal dry-daylight operating mode;
- manual takeover;
- abort;
- return-to-home.

## 15. Explicitly Excluded from Version 1.0

Version 1.0 excludes:

- custom airframe;
- custom motors;
- custom ESCs;
- custom flight controller;
- user-defined priority zones, guided routes, and custom route drafts;
- automatic multi-flight stitching;
- fog, mist, rain, precipitation, and degraded-visibility operation;
- custom low-level stabilization;
- crop spraying;
- treatment recommendations;
- chemical dosage recommendations;
- definitive agronomic diagnosis;
- multispectral imaging;
- hyperspectral imaging;
- thermal imaging;
- LiDAR;
- drone swarms;
- multiple simultaneous drones;
- multiple simultaneous field missions;
- research-grade autonomous obstacle avoidance;
- unsupported rain operation;
- operation without visual line of sight where prohibited;
- all-weather guarantees;
- guaranteed disease classification from high-altitude imagery;
- fully unsupervised takeoff without operator approval.

## 16. Future Extensions

Possible future extensions include:

- broader crop support;
- multispectral sensing;
- thermal sensing;
- onboard TensorRT inference;
- weather-station integration;
- dedicated rain and visibility sensors;
- automated condensation detection;
- historical field comparison;
- multi-season analytics;
- advanced severity estimation;
- obstacle awareness;
- multi-drone coordination;
- cloud fleet management;
- agronomist-reviewed treatment information;
- farm-management-system integration.

## 17. Known Assumptions and Unresolved Decisions

The following remain intentionally unresolved until their applicable deployment-readiness gates:

- final crop used for first field validation;
- final drone model;
- final camera model;
- exact weather rating;
- exact legal and local flight constraints;
- exact altitude and speed limits;
- exact wind thresholds;
- exact light-rain threshold;
- exact minimum visibility;
- exact battery reserve;
- exact ground sampling distance;
- whether screening runs onboard or on the ground station;
- final method for measuring visibility;
- final method for detecting rain;
- final field size;
- final revisit-target capacity per battery.

These values must be resolved through hardware selection, manufacturer documentation, simulation, field tests, and applicable regulations.

## 18. Scope Acceptance Criteria

The system scope is considered satisfied when:

1. the supported environment is documented;
2. crop and sensor assumptions are explicit;
3. field and obstacle assumptions are explicit;
4. nominal survey and revisit parameters are defined provisionally;
5. battery reserve policy is defined;
6. the dry-daylight production envelope is defined;
7. unsupported precipitation and degraded visibility block start or trigger safe return/landing;
8. mission-start refusal conditions are explicit;
9. runtime abort and return conditions are explicit;
10. one-sector mission and coverage semantics are explicit;
11. v1.0 inclusions and exclusions are explicit;
12. unresolved hardware-dependent limits are identified;
13. operator supervision and manual intervention remain mandatory.

## 19. References and Safety Basis

The scope uses the following principles:

- required visual line of sight must be preserved during applicable operations;
- common non-weather-rated camera drones may prohibit flight in rain or fog;
- weather-resistant enterprise aircraft may support limited moisture exposure only within their documented ratings;
- PX4 supports configurable safety and high-wind failsafe behavior;
- manufacturer, legal, and operator limits take precedence over project defaults.

The selected drone's official operating manual and current local regulations shall be reviewed before real-flight configuration.

## 20. Final Scope Statement

PlantGuard UAV v1.0 operates on one predefined open agricultural field at a time using one operator-authorized programmable RGB drone.

The supported production condition is dry daylight weather with adequate visibility and wind inside the qualified limit. Fog, mist, rain, precipitation, night operation, and degraded-visibility operation are excluded from v1.0.

The system shall refuse mission start or return/land safely when the qualified operating conditions cannot be maintained.
