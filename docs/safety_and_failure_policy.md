# PlantGuard UAV — Safety and Failure Policy

## Document Control

| Field | Value |
|---|---|
| Product | PlantGuard UAV |
| Document | Safety and Failure Policy |
| Target release | v1.0 |
| Status | Active |
| Related documents | `docs/product_requirements.md`, `docs/system_scope.md`, `docs/data_and_decision_contracts.md` |
| Last updated | 2026-07-16 |

## 1. Document Purpose

This document defines the safety, preflight, runtime failure, operator override, return-to-home, partial-data preservation, and recovery policy for PlantGuard UAV v1.0.

It establishes:

- which conditions must block takeoff;
- which conditions may produce warnings;
- which failures may allow degraded operation;
- which failures must cancel survey or revisit activity;
- when return-to-home is required;
- when manual takeover takes priority;
- how the system behaves when AI, backend, camera, telemetry, GPS, storage, weather, or route validation fails;
- how partial mission data is preserved;
- how interrupted processing may resume;
- how an incomplete physical flight may be continued safely through a separately authorized recovery mission.

The policies in this document define product behavior. Hardware-specific numerical thresholds shall be stored in versioned configuration after final aircraft, camera, flight-controller, and field-test decisions are available.

## 2. Safety Principles

PlantGuard UAV v1.0 shall follow these principles.

### 2.1 Safety Has Priority Over Mission Completion

Completing a field scan, revisit, or disease prediction is never more important than:

- maintaining safe flight;
- preserving operator control;
- respecting battery reserve;
- remaining inside approved boundaries;
- preserving visual line of sight where required;
- complying with the selected aircraft's limits;
- returning or landing safely.

### 2.2 Native Flight-Controller Safety Remains Authoritative

PlantGuard UAV shall not disable or override the selected flight controller's:

- battery failsafe;
- geofence;
- loss-of-link behavior;
- position-loss behavior;
- return-to-home behavior;
- critical landing behavior;
- manual-control priority.

Application-level mission logic shall operate above, not instead of, these mechanisms.

### 2.3 Manual Control Has Priority

The operator must always retain access to:

```text
Pause Mission
Resume Mission
Abort Mission
Return Home
Manual Takeover
```

Manual takeover immediately supersedes PlantGuard autonomy.

### 2.4 No Silent Failure

Every important failure shall produce:

- a machine-readable event;
- an operator-visible message;
- a timestamp;
- the active mission phase;
- the action taken;
- the data preserved;
- the next recommended action.

### 2.5 Partial Data Must Be Preserved

A mission that is aborted, degraded, or failed shall retain every valid artifact produced before termination.

### 2.6 Flight and AI Processing Must Be Decoupled

An AI or backend process failure must not destabilize the aircraft.

The aircraft must retain safe flight and native failsafe behavior even when:

- the dashboard crashes;
- the mission worker crashes;
- the screening model fails;
- the disease classifier fails;
- the database becomes unavailable;
- the ground-station network connection is interrupted.

## 3. Safety Severity Levels

Every preflight and runtime condition shall be classified into one of the following levels.

| Level | Meaning | Default behavior |
|---|---|---|
| `normal` | All required systems are operating correctly | Continue |
| `warning` | Non-critical condition requires operator awareness | Continue after display |
| `degraded` | A subsystem is impaired but safe restricted operation remains possible | Continue with reduced functionality |
| `return_required` | Mission objective can no longer be completed safely | Cancel remaining work and return home |
| `emergency` | Normal return may be unsafe or impossible | Apply native failsafe, manual takeover, or safe landing |

A lower-severity application decision shall never override a higher-severity flight-controller condition.

## 4. Preflight Check Results

Every preflight check shall return one of:

```text
PASS
WARNING
BLOCKED
```

### 4.1 PASS

The requirement is satisfied.

Examples:

```text
GPS healthy
Camera test capture succeeded
Battery estimate sufficient
Route inside approved boundary
```

### 4.2 WARNING

The mission may proceed only after the condition is shown clearly to the operator.

Examples:

```text
Battery below preferred level but still safely sufficient
Reduced storage margin
Optional subsystem unavailable
```

Warnings must never be used to bypass a hard safety requirement.

### 4.3 BLOCKED

The aircraft shall remain disarmed.

A hard blocker shall not be overridden through the PlantGuard dashboard.

Examples:

```text
No valid home position
Insufficient battery for mission and safe return
Route intersects exclusion zone
Flight controller unhealthy
Manual takeover unavailable
Selected hardware not approved for current weather
```

## 5. Mandatory Technical-Preflight Checks

### 5.1 Operator and Control Checks

The system shall verify:

- operator is present;
- manual controller or equivalent manual-control mechanism is available;
- abort control is available;
- return-to-home control is available;
- takeoff area is clear;
- operator confirms people, vehicles, and livestock are clear of the launch area;
- operator confirms actual conditions match the dry-daylight production envelope.

The following are hard blockers:

```text
manual takeover unavailable
return-to-home unavailable
abort control unavailable
unsafe takeoff area
operator unable to supervise
```

### 5.2 Field and Route Checks

The system shall verify:

- field record exists;
- field boundary is valid;
- home location is valid;
- takeoff area is valid;
- survey route remains inside the approved boundary;
- revisit route remains inside the approved boundary;
- route avoids exclusion zones;
- altitude clears crops and known obstacles;
- route duration can be estimated;
- mission distance can be estimated;
- required geofence is active;
- route does not contain malformed or duplicate waypoints that create unsafe motion.

The following are hard blockers:

```text
missing field boundary
invalid field geometry
missing home location
route leaves approved area
route intersects exclusion zone
unresolved obstacle risk
required geofence unavailable
route duration cannot be estimated
mission cannot satisfy battery reserve
```

### 5.3 Drone and Flight-Controller Checks

The system shall verify:

- vehicle connection;
- flight-controller health;
- required sensor calibration;
- propulsion-system health;
- position estimate;
- home position;
- battery telemetry;
- failsafe configuration;
- armed-state consistency;
- flight-mode availability;
- return-to-home configuration.

The following are hard blockers:

```text
flight controller unhealthy
required calibration missing
critical vehicle warning
position estimate invalid
home position unavailable
battery telemetry unavailable
return-to-home configuration invalid
```

### 5.4 GPS and Positioning Checks

The system shall verify:

- current position is available;
- home position is recorded;
- positioning quality meets configured minimum;
- altitude estimate is valid;
- route can be navigated using the current positioning source.

Before takeoff, the following are hard blockers:

```text
no valid position
no valid home position
position quality below configured minimum
altitude estimate unavailable
```

### 5.5 Battery Checks

The system shall verify that estimated energy is sufficient for:

```text
planned survey
+
expected hover and capture time
+
planned revisit allowance
+
return-to-home
+
landing
+
configured reserve
```

The default planning policy is:

```text
preferred takeoff charge: at least 90%
maximum planned usable consumption: approximately 70%
minimum planned landing reserve: at least 30%
```

These are provisional configuration defaults, not universal hardware limits.

The following are hard blockers:

```text
battery estimate unavailable
battery below configured start threshold
predicted landing reserve below configured minimum
battery health reports critical fault
```

### 5.6 Camera and Storage Checks

The system shall verify:

- camera connected;
- test image captured successfully;
- image file readable;
- lens unobstructed;
- no unacceptable condensation;
- image exposure and sharpness are usable;
- storage writable;
- estimated storage sufficient;
- timestamps recorded;
- location association available;
- gimbal or camera mount healthy where applicable.

The following are hard blockers:

```text
camera unavailable
test capture fails
storage full
storage not writable
lens heavily obscured
unacceptable condensation
required capture metadata unavailable
```

### 5.7 AI and Computing Checks

For the normal one-button mission, the system shall verify:

- healthy/unhealthy screening model available;
- disease-classification model available;
- model metadata available;
- preprocessing configuration valid;
- thresholds/configuration valid;
- required compute runtime available;
- mission orchestrator healthy;
- required worker or service reachable;
- sufficient local storage for mission artifacts;
- time synchronization acceptable.

For normal v1.0 operation:

```text
screening model unavailable
→ BLOCKED

disease-classification model unavailable
→ BLOCKED
```

A future explicitly selected `survey_only` mode may use different requirements, but normal one-button operation shall not silently downgrade into survey-only behavior.

### 5.8 Weather and Visibility Checks

The configured production operating mode shall be:

```text
nominal_dry_daylight
```

The system shall verify:

- actual conditions match the dry-daylight production envelope;
- wind remains inside configured limit;
- visual line of sight can be maintained;
- image-quality test passes;
- condensation is acceptable;
- route and obstacle clearance remain observable;
- operator judges the conditions safe.

The following are hard blockers:

```text
rain or precipitation detected
fog or mist detected
inadequate daylight or visibility
wind exceeds configured limit
image-quality test repeatedly fails
operator judges conditions unsafe
```

Changing altitude, speed, or route length shall not override a hard weather or visibility blocker.

## 6. Preflight Decision Contract

Technical preflight shall produce:

```json
{
  "mission_id": "mission_000001",
  "overall_status": "PASS",
  "checks": [
    {
      "check_id": "battery_capacity",
      "status": "PASS",
      "severity": "normal",
      "message": "Estimated landing reserve is above the configured minimum."
    }
  ],
  "blocking_reasons": [],
  "warnings": [],
  "operator_approval_required": true
}
```

Technical-preflight PASS or permitted WARNING moves the workflow to `awaiting_operator_approval`; missing approval does not change the technical-preflight result.

The system may arm only when:

```text
all hard checks pass
+
operator approval references the current non-expired preflight snapshot
+
final takeoff validation finds no new blocker
```

## 7. Battery Runtime Policy

### 7.1 Survey Continuation

Survey may continue only while projected landing reserve remains above the configured minimum.

The system shall not wait for the battery percentage itself to reach the reserve threshold when current route, wind, or distance predicts an unsafe landing reserve.

### 7.2 Revisit Start

Revisit shall begin only when estimated energy is sufficient for:

```text
selected revisit sites
+
return-to-home
+
landing
+
configured reserve
```

### 7.3 Partial Revisit Selection

When all sites cannot be revisited safely:

1. rank sites by configured priority;
2. select the safe subset;
3. preserve excluded sites;
4. mark excluded sites with `revisit_skipped_battery`;
5. recommend manual inspection for unresolved sites;
6. return home with reserve intact.

### 7.4 Mandatory Return

Return-to-home shall be triggered when:

```text
projected landing reserve would be violated
configured return threshold is reached
energy requirement increases unexpectedly
battery telemetry becomes unreliable
flight controller activates battery failsafe
```

### 7.5 Critical Battery

Critical-battery handling belongs to the flight controller.

PlantGuard shall not suppress, postpone, or override a critical-battery failsafe.

## 8. GPS and Positioning Failure Policy

### 8.1 Before Takeoff

Missing or invalid position:

```text
BLOCKED
```

### 8.2 Temporary Runtime Degradation

When position quality degrades temporarily:

```text
stop issuing new application-level navigation decisions
→ notify operator
→ preserve last valid location
→ allow configured flight-controller behavior
```

### 8.3 Persistent Runtime Degradation

When valid navigation remains possible but quality stays degraded:

```text
cancel remaining mission
→ command return-to-home
```

### 8.4 Position Loss Affecting Return-to-Home

When return-to-home may itself be unreliable:

```text
do not blindly command application-level return
→ defer to native position-loss failsafe
→ notify operator
→ permit manual takeover when safe
→ use safe landing behavior where configured
```

The event log shall preserve:

- time of degradation;
- last valid position;
- active mission phase;
- last valid altitude;
- battery state;
- action selected;
- final known state.

## 9. Telemetry Loss Policy

Telemetry-loss safety shall be owned primarily by the aircraft and flight controller.

### 9.1 Short Interruption

The application shall:

```text
display connection warning
preserve last-known telemetry
stop issuing non-essential commands
wait for configured reconnection interval
allow native flight behavior to continue
```

### 9.2 Persistent Interruption

The aircraft shall follow its configured loss-of-link behavior, such as:

```text
hold
return home
land
```

PlantGuard shall record:

```text
telemetry-loss timestamp
last known location
last known battery
active mission phase
configured loss-of-link action
whether connection returned
final known vehicle state
```

## 10. Camera Failure Policy

### 10.1 Before Takeoff

```text
camera failure
→ BLOCKED
```

### 10.2 Single Survey Capture Failure

```text
retry according to capture policy
→ if retry succeeds, continue
→ otherwise record failed capture
```

### 10.3 Repeated Survey Capture Failure

When consecutive or percentage-based capture failures exceed configured limits:

```text
pause useful mission progress
→ attempt safe camera recovery
→ perform sample capture
```

If recovery fails:

```text
cancel survey
→ preserve completed images
→ disable automatic revisit
→ return home
```

### 10.4 Single Revisit Capture Failure

```text
retry safely
→ if still unsuccessful, mark site capture_failed
→ continue to next site when safe
```

### 10.5 Global Camera Failure During Revisit

```text
cancel remaining revisits
→ return home
→ preserve completed sites
→ mark unresolved sites for manual inspection
```

## 11. AI Inference Failure Policy

### 11.1 Screening Failure During Survey

The preferred response is:

```text
continue safe image collection
→ preserve images and metadata
→ disable automatic revisit generation
→ complete survey only while safety and battery permit
→ return home
→ resume analysis later
```

The mission may end with:

```text
survey_completed_analysis_failed
```

### 11.2 Partial Screening Failure

Valid completed results shall remain saved.

Processing shall resume later from the first incomplete or failed item rather than discarding completed work.

### 11.3 Disease-Classification Failure During Revisit

When the revisit route was generated safely before classifier failure:

```text
continue capturing planned revisit images when safe
→ do not force disease output
→ return home
→ perform classification later
```

Affected sites shall retain:

```text
classification_pending
```

### 11.4 Invalid Model Output

Invalid output includes:

```text
NaN confidence
unknown class identifier
missing model metadata
malformed output shape
confidence outside valid range
unsupported label
```

The system shall:

```text
reject invalid prediction
→ preserve input evidence
→ record model-contract failure
→ exclude result from automatic final decision
```

## 12. Backend and Application Failure Policy

### 12.1 Dashboard Failure

A dashboard failure shall not remove:

- physical manual control;
- flight-controller failsafes;
- active return-to-home capability;
- native mission safety.

The mission service may continue if healthy.

### 12.2 Mission-Orchestrator Failure

The system shall:

```text
stop issuing new application-level waypoints
preserve last completed state
use native hold/return/failsafe behavior
recover logs after restart
```

### 12.3 Worker Failure

The system shall:

```text
mark active processing job failed
preserve completed artifacts
retry according to configured policy
resume from checkpoint when possible
```

### 12.4 Database Failure

When persistent storage becomes unavailable:

```text
stop creating new decisions that cannot be audited
→ write to temporary local event storage if available
→ return home if safe traceability cannot continue
```

### 12.5 Cloud or Internet Failure

Safety-critical flight shall not require a cloud service.

Where local control remains healthy:

```text
continue local operation
→ queue synchronization for later
```

Where required local services fail:

```text
apply the relevant local failure policy
```

## 13. Weather Degradation During Flight

### 13.1 Increasing Rain

The system shall re-evaluate:

- hardware weather limit;
- lens visibility;
- image quality;
- vehicle stability;
- visual line of sight;
- return energy.

When approved precipitation limits are exceeded:

```text
cancel mission
→ return home
```

### 13.2 Increasing Fog or Mist

When required visual line of sight or route visibility is lost:

```text
cancel mission
→ return home when navigation remains valid
→ otherwise apply native safe-landing/manual-control policy
```

### 13.3 Repeated Image-Quality Failure

When configured failure limits are reached, the system may attempt:

```text
reduce altitude within safe limits
reduce speed
increase overlap
capture new sample images
```

If the adapted sample still fails:

```text
cancel current survey or revisit
→ return home
→ preserve partial mission
```

## 14. Route and Geofence Failure Policy

### 14.1 Invalid Generated Revisit Waypoint

```text
reject waypoint
→ do not upload it
→ mark site revisit_skipped_route_invalid
→ preserve site for report
```

### 14.2 Route Invalidation Before Takeoff

```text
BLOCKED
```

### 14.3 Unexpected Vehicle Deviation

The system shall:

```text
notify operator
→ stop issuing new application commands
→ apply hold or return policy
```

PlantGuard shall never disable the native geofence merely to complete a survey or revisit.

## 15. Operator Command Policy

### 15.1 Pause Mission

Pause means:

```text
pause mission progression
→ enter safe hold where supported
→ preserve current state
→ await resume, return-home, abort, or manual takeover
```

Pause is accepted only when PX4 can enter a confirmed hold and link, geofence, energy, return, landing, reserve, and environmental constraints remain safe. Otherwise it is rejected or converted into return-home or controlled landing.

### 15.2 Resume Mission

Resume requires:

```text
confirmed hold created by the current mission
+ explicit operator request
+ current safety revalidation
+ unchanged authoritative mission context
```

Resume is rejected after process restart, manual takeover, loss of authoritative context, or link-loss recovery. Those cases require a new recovery mission, technical preflight, and operator approval. `ResumeMission` never means `ResumeJob`.

### 15.3 Abort Mission

Normal abort means:

```text
cancel remaining survey and revisit work
→ preserve partial data
→ return home by default
```

Abort shall not normally stop motors while airborne.

### 15.4 Return Home

```text
cancel remaining autonomous work
→ command return-to-home
→ keep workflow active and set mission activity to return_home
```

No survey or revisit work may restart after return-to-home begins.

### 15.5 Manual Takeover

```text
operator control immediately supersedes autonomy
→ PlantGuard stops navigation commands
→ mission marked interrupted or aborted
→ data preserved
```

### 15.6 Emergency Landing

Emergency landing shall follow the selected aircraft and flight-controller procedures.

It is used only when normal return is unsafe or impossible.

## 16. Failure Behavior by Mission Phase

### 16.1 Before Takeoff

Any hard blocker:

```text
remain disarmed
→ display exact failure
→ allow recheck after correction
```

### 16.2 During Takeoff

Critical failure:

```text
stop mission progression
→ land or apply native failsafe
```

### 16.3 During Survey

Allowed responses include:

```text
continue normally
continue in degraded mode
continue image collection but disable AI revisit
cancel survey and return
manual takeover
```

### 16.4 During Initial Analysis

When analysis can be retried safely:

```text
retry within configured time and battery budget
```

When analysis cannot complete before safe return:

```text
do not begin revisit
→ return home
→ process later
```

### 16.5 During Revisit

One-site failure:

```text
record failure
→ continue to next site when safe
```

Global revisit failure:

```text
cancel remaining sites
→ return home
```

### 16.6 During Return-to-Home

No new mission work may begin.

### 16.7 During Landing

No new survey, analysis-triggered flight, or revisit command may be issued.

## 17. Partial-Mission Preservation

The system shall save progress incrementally.

The following shall be preserved when available:

```text
completed waypoints
captured images
capture failures
screening predictions
suspicious sites
revisit targets
completed revisits
unvisited sites
classification outputs
model errors
operator commands
telemetry events
weather events
failure reason
configuration snapshot
```

A failed mission must never be reported as completed.

## 18. Final Mission Status Values

The system shall support final statuses such as:

```text
completed
completed_with_warnings
survey_completed_revisit_incomplete
survey_completed_analysis_failed
aborted_by_operator
returned_due_to_battery
returned_due_to_weather
returned_due_to_camera_failure
returned_due_to_position_failure
returned_due_to_system_failure
manual_takeover
failed
```

Each final status shall include a reason and preserved-data summary.

## 19. Recovery and Resume Policy

### 19.1 Processing Recovery

The following may resume from checkpoints:

- image validation;
- image tiling;
- healthy/unhealthy screening;
- suspicious-site grouping;
- disease classification;
- mapping;
- report generation.

Already completed valid stages shall not rerun unless explicitly requested or invalidated by configuration changes.

### 19.2 Physical Flight Recovery

A physical flight shall never resume automatically after:

- software restart;
- mission-service crash;
- landing;
- operator abort;
- manual takeover;
- battery return;
- weather return;
- critical failure.

To continue incomplete coverage:

1. create a new recovery mission;
2. link it to the original mission;
3. calculate only missing safe coverage;
4. run complete preflight again;
5. require new operator approval;
6. create a new mission identifier.

Example:

```json
{
  "mission_id": "mission_000002",
  "parent_mission_id": "mission_000001",
  "mission_type": "recovery"
}
```

## 20. Revisit Recovery Policy

When revisit is incomplete:

- completed sites remain completed;
- unfinished sites remain unresolved;
- each unresolved site retains its reason;
- manual inspection is recommended where needed;
- a later revisit-recovery mission may be generated;
- new preflight and operator approval are required.

## 21. Operator-Visible Message Contract

Every important warning or failure shall state:

```text
what happened
when it happened
whether the drone is currently safe
what the drone is doing now
what data was preserved
what the operator should do next
```

Example:

```text
Camera connection lost during survey.

The remaining survey and automatic revisit have been cancelled.
The drone is returning home.
127 images and their location data were saved.
After the camera issue is corrected, analysis can resume or a recovery mission can be created.
```

The application shall avoid vague messages such as:

```text
Something went wrong
Unknown failure
Error 500
```

## 22. Failure Event Contract

Each failure event should contain:

```json
{
  "event_id": "event_000001",
  "mission_id": "mission_000001",
  "timestamp": "ISO-8601 timestamp",
  "workflow_state": "active",
  "mission_activity": "survey",
  "vehicle_state": "in_flight",
  "component": "camera",
  "severity": "return_required",
  "code": "camera_unavailable",
  "message": "Camera connection was lost during survey.",
  "system_action": "return_to_home",
  "operator_action_required": false,
  "data_preserved": true,
  "recovery_allowed": true
}
```

## 23. Failure Response Matrix

| Failure | Detection | Severity | System action | State transition | Final reporting |
|---|---|---|---|---|---|
| Operator approval missing | Final takeoff authorization | Blocked | Remain disarmed | `awaiting_operator_approval` | Request authorized approval |
| Low start battery | Battery estimate | Blocked | Remain disarmed | workflow `preparing`, activity `technical_preflight` | Show required reserve |
| Projected reserve violation | Energy forecast | Return required | Cancel work and return | workflow `active`, activity `return_home` | Mark incomplete sites |
| GPS invalid before takeoff | Position health | Blocked | Remain disarmed | workflow `preparing`, activity `technical_preflight` | Show positioning failure |
| GPS degrades in flight | Position health | Return/emergency | Stop new commands; apply return/failsafe | workflow `active`/`failed`, activity `return_home` | Preserve last valid state |
| Telemetry loss | Link monitor | Warning/return | Defer to native link-loss policy | Depends on aircraft | Record last known state |
| Camera unavailable before flight | Camera test | Blocked | Remain disarmed | workflow `preparing`, activity `technical_preflight` | Show camera failure |
| Camera fails during survey | Capture monitor | Return required | Preserve images; disable revisit; return | workflow `active`, activity `return_home` | Mark survey incomplete |
| One revisit capture fails | Capture retry policy | Degraded | Mark site failed; continue | workflow `active`, activity `revisit` | Manual inspection for site |
| Screening process fails | Worker/model health | Degraded | Continue safe capture; disable auto revisit | workflow `active`, activity `survey` | Analysis pending/failed |
| Disease classifier fails | Worker/model health | Degraded | Preserve revisit images; classify later | workflow `active`, activity `revisit` | Classification pending |
| Dashboard crashes | Service health | Warning | Retain flight safety and controller access | No forced change | Log UI outage |
| Mission orchestrator crashes | Process health | Return required | Stop new commands; use native safety behavior | workflow `failed`; vehicle uses native return/landing behavior | Preserve checkpoint |
| Database unavailable | Persistence health | Degraded/return | Use local queue or return | Depends on durability | Record storage failure |
| Wind rises above limit | Weather monitor | Return required | Cancel and return | workflow `active`, activity `return_home` | Mark weather return |
| Fog or mist detected | Operator/visibility check | Return/emergency | Return or safe landing | workflow `active`/`failed`, activity `return_home` | Mark environment failure |
| Route leaves boundary | Route validator | Blocked | Reject route | workflow `preparing`, activity `configuration` | Show invalid route |
| Invalid revisit waypoint | Route validator | Degraded | Skip site | workflow `active`, activity `same_flight_decision` | Manual inspection |
| Operator abort | Operator command | Return required | Cancel mission and return | workflow `active`, activity `return_home`, then `aborted` | Mark aborted |
| Manual takeover | Controller input | Emergency priority | Stop autonomy | `aborted` | Mark manual takeover |

## 24. Hard Blockers

The following cannot be overridden through the dashboard:

```text
operator approval missing
manual takeover unavailable
return-to-home unavailable
critical flight-controller fault
invalid or missing position before takeoff
invalid home position
insufficient safe battery
invalid field boundary
unsafe route
geofence unavailable where required
unknown obstacle risk
camera unavailable
storage unavailable
required model unavailable in normal mode
unsupported weather
VLOS unavailable
operator judges conditions unsafe
```

## 25. Warning-Only Conditions

Warnings may include:

```text
battery below preferred but above safe minimum
reduced storage margin
optional service unavailable
non-critical image-quality reduction
partial revisit capacity
```

A warning must become a blocker or return condition when its configured safe boundary is crossed.

## 26. Degraded Operation Rules

The system may continue with a degraded non-environmental subsystem only when:

- flight safety remains valid;
- operator control remains available;
- data traceability remains sufficient;
- the degraded behavior is explicitly defined;
- the operator is informed;
- the mission can still return with reserve.

Examples:

```text
screening offline but image capture healthy
one revisit site capture failed
temporary dashboard outage
```

This section does not permit operation outside the dry-daylight environmental envelope.

## 27. Authoritative Safety Decisions

PlantGuard UAV v1.0 freezes the following rules:

1. Hard safety failures cannot be overridden from the dashboard.
2. Normal Abort cancels the mission and returns home; it does not stop motors in flight.
3. Manual takeover always supersedes autonomy.
4. Revisit starts only when revisit, return, landing, and reserve are feasible.
5. When all sites cannot be revisited, the system selects a safe priority subset and reports the rest.
6. Complete camera failure ends useful autonomous inspection and triggers return-home.
7. Screening failure may allow safe image collection to finish, but automatic revisit is disabled.
8. Disease-classifier failure may allow already planned revisit image collection to finish for later processing.
9. Dashboard or backend failure must not remove native failsafes or physical manual control.
10. Partial mission data is always preserved.
11. Data processing may resume from checkpoints.
12. Physical flight never resumes automatically after interruption.
13. A continued physical mission after restart or authority loss requires a new recovery mission, technical preflight, and new operator approval.
14. PlantGuard never disables geofence or native safety systems merely to finish a mission.
15. Leaving the dry-daylight production envelope starts return-home or controlled landing; mission adaptation does not authorize continued degraded-weather operation.
16. Numerical battery, GPS, wind, retry, timeout, and image-quality limits remain hardware-specific versioned configuration.

## 28. Safety-Baseline Acceptance Criteria

The safety and failure policy is complete when:

- hard blockers are defined;
- warning behavior is defined;
- degraded behavior is defined;
- battery start, continuation, revisit, and return logic are defined;
- GPS and positioning failure behavior is defined;
- telemetry-loss behavior is defined;
- camera-failure behavior is defined;
- AI-failure behavior is defined;
- backend-failure behavior is defined;
- weather-degradation behavior is defined;
- geofence and route-failure behavior is defined;
- operator commands are defined;
- failure behavior is defined by mission phase;
- partial mission preservation is defined;
- physical-flight recovery requires new approval;
- every important failure includes detection, severity, action, state transition, visible message, preserved evidence, and recovery behavior.

## 29. Final Safety Statement

PlantGuard UAV v1.0 is designed to complete autonomous field inspection only while safety, operator control, route validity, hardware health, weather support, image capture, and battery reserve remain acceptable.

When these conditions fail, the system shall:

```text
restrict functionality
or
cancel the remaining mission
or
return home
or
defer to native failsafe/manual control
```

No disease prediction, field-coverage target, or revisit target is allowed to override safe recovery of the aircraft.
