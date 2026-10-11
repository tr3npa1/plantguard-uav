# Inspection Flight Configuration

## Purpose and Current Boundary

`src/plantguard_uav/domain/inspection_configuration.py` defines the versioned survey/revisit flight-parameter portion of a future inspection configuration. These are immutable domain values that can be validated and serialized as JSON. They are not the complete mission configuration snapshot, an approved operating profile, or a command to a drone.

Every flight parameter is required. The module supplies no default altitude, speed, overlap, or operational profile. Numeric values used in unit tests are synthetic test inputs, not recommendations or deployment presets.

`src/plantguard_uav/adapters/inspection_configuration.py` can read this contract from an explicitly selected local JSON file. A read-only application service verifies that the loaded configuration matches a caller's requested ID and revision. A development/testing-only HTTP endpoint now exposes this service using an explicitly wired server-side source. The existing saved-field catalogue and detail endpoints remain unchanged. There is still no configuration registry, configuration database table, field writer, or flight execution.

## Models and Fields

### SurveyConfiguration

| Field | Meaning and unit | Structural validation |
| --- | --- | --- |
| `altitude_agl_m` | Requested nominal survey altitude above ground level, in metres | Required finite number greater than zero |
| `speed_m_s` | Requested nominal survey speed, in metres per second | Required finite number greater than zero |
| `front_overlap_fraction` | Requested forward image overlap as a fraction of one | Required finite number greater than or equal to zero and less than one |
| `side_overlap_fraction` | Requested sideways image overlap as a fraction of one | Required finite number greater than or equal to zero and less than one |
| `schema_version` | Version of this object's data format | Only `"1.0"`, supplied by default |

### RevisitConfiguration

| Field | Meaning and unit | Structural validation |
| --- | --- | --- |
| `altitude_agl_m` | Requested nominal revisit altitude above ground level, in metres | Required finite number greater than zero |
| `speed_m_s` | Requested nominal revisit speed, in metres per second | Required finite number greater than zero |
| `schema_version` | Version of this object's data format | Only `"1.0"`, supplied by default |

### InspectionFlightConfiguration

| Field | Meaning | Structural validation |
| --- | --- | --- |
| `configuration_id` | Identifier supplied for the configuration | Required nonblank string; surrounding whitespace removed |
| `configuration_version` | Revision identifier for this configuration's values | Required nonblank string; surrounding whitespace removed |
| `operating_environment` | Requested production operating category | Required explicit `"nominal_dry_daylight"` |
| `survey` | Survey flight parameters | Required validated `SurveyConfiguration` |
| `revisit` | Revisit flight parameters | Required validated `RevisitConfiguration` |
| `schema_version` | Version of the combined object's data format | Only `"1.0"`, supplied by default |

All three models reject unknown fields and unsupported schema versions. They are publicly exported from `plantguard_uav.domain`.

## Numeric and Cross-Field Rules

Flight parameters accept Python `int` or `float` values, including the corresponding JSON numbers. Accepted integers are normalized to floats. Booleans, numeric strings, bytes, null values, decimal objects, and arbitrary objects with numeric-conversion methods are rejected. NaN, positive/negative infinity, and integers too large to represent as a finite float are rejected.

Image overlaps use fractions, not percentage numbers. For representation only, a fraction of `0.7` means 70%; it is not a recommended overlap. Zero is structurally representable. An overlap of one or more is outside the declared format. These bounds do not establish a qualified production minimum or guarantee usable image coverage.

After validating the nested models, the combined model requires:

```text
revisit.altitude_agl_m < survey.altitude_agl_m
```

Equal or higher revisit AGL targets are rejected. This implements the nominal lower-altitude revisit relationship. It compares requested heights above ground, not absolute altitudes or a safe descent trajectory. There is no imposed relationship between survey and revisit speed; the source contracts do not establish one.

No universal upper altitude, upper speed, or production overlap threshold is invented here. Those limits require a qualified configuration and independent safety validation.

## Altitude and Environment Semantics

AGL means above ground level. It is not altitude above mean sea level and not clearance above the crop canopy. No canopy-to-AGL conversion is performed. Provisional canopy-relative figures elsewhere in the scope documents are not used as AGL settings.

These fields describe requested nominal targets, not measured telemetry. The models do not establish terrain clearance, canopy clearance, the source or uncertainty of measured altitude, or whether the vehicle can maintain the target along a route.

`operating_environment` is separate from the application's `development`, `testing`, and `production` settings. Requiring the literal `nominal_dry_daylight` records the requested operating category; it does not measure weather or prove that current conditions satisfy that category.

## Versions, Immutability, and Revalidation

`schema_version` identifies the shape and meaning of a serialized contract. `configuration_version` identifies a revision of the supplied configuration values. The latter remains an opaque string: these models do not generate, increment, register, or enforce uniqueness of configuration revisions.

The local inspection-model base inherits the existing `ContractModel` rules: unknown fields are rejected, instances are frozen, human-readable validation errors hide raw input values, and `model_copy` revalidates requested changes. Machine-readable Pydantic error details can still contain inputs and must not be exposed indiscriminately.

The inspection models additionally use `revalidate_instances="always"`. Existing nested model instances are checked again when passed through normal model validation. This catches invalid objects created using Pydantic's trusted `model_construct` escape hatch before they are accepted into a normally validated configuration. This local setting does not change the existing field, state, or geometry contracts. Direct use of `model_construct` itself still bypasses validation and is not an ingestion path.

To change a configuration, create a validated replacement or call `model_copy(update=...)`. A copied combined configuration must still satisfy the cross-field altitude rule. Copying does not automatically assign a new configuration version; version lifecycle and snapshot capture remain future work.

## Explicit Local JSON Loading

The adapter exposes two operations:

```python
parse_inspection_configuration_json(payload: bytes) -> InspectionFlightConfiguration
load_inspection_configuration(path: Path) -> InspectionFlightConfiguration
```

The parser accepts only UTF-8 JSON bytes, without a byte-order mark (BOM), representing one object with the fields listed above. The file loader requires an explicit `pathlib.Path`; it does not search for a file or provide a default path. Relative paths are resolved by the process's current working directory, so callers should prefer an explicit absolute path when location matters.

Loading follows this sequence:

1. Check that the selected path refers to a regular file.
2. Open it in binary read-only mode, and check the opened handle is also a regular file.
3. Read at most `MAX_INSPECTION_CONFIGURATION_BYTES + 1` bytes, then close the handle.
4. Reject inputs exceeding **64 KiB (65,536 bytes)**. Reading one extra byte distinguishes a file exactly at the limit from a larger one; the earlier file-size metadata is not trusted to bound the read.
5. Decode UTF-8 and parse JSON, rejecting repeated decoded keys at every object level, including escaped-equivalent keys. Reject NaN, infinity tokens, and numeric literals that overflow to infinity.
6. Reject non-object roots and strings containing unpaired Unicode surrogate escapes. Malformed JSON, decoder recursion-limit failures, and integer-digit-limit failures become controlled errors.
7. Call `InspectionFlightConfiguration.model_validate` to enforce the domain validation rules and return the frozen configuration. Numeric and cross-field rules are not duplicated in the adapter.

The size cap is a technical input-resource limit, not a flight limit. JSON is an implementation choice permitted by the scope baseline. This small survey/revisit input file is **not** the future full `configuration/mission_config.yaml` snapshot described in the data contracts; that snapshot contract is unchanged.

Every call reads the current selected file. There is no cache, environment-variable override, YAML fallback, implicit preset, or application-startup file read. The loader itself remains independent of HTTP; the optional server-wired route described below calls it through the existing source and service. The existing application-settings loader is unchanged. Successful and failed reads do not modify the source file; tests use temporary synthetic inputs rather than real operational profiles.

### Controlled Failures

`InspectionConfigurationError` inherits from `ConfigurationError`. Its public message is always `Inspection configuration could not be loaded.` Its structured context contains only the operation `load_inspection_configuration` and one reason:

| Reason | Meaning |
| --- | --- |
| `invalid_input` | The bytes parser received a different input type |
| `file_unavailable` | File metadata, opening, reading, or closing failed, or the supplied path was invalid |
| `not_regular_file` | The path or opened handle refers to a directory or special file |
| `input_too_large` | The input exceeds 65,536 bytes |
| `invalid_encoding` | Invalid UTF-8 bytes or an unpaired surrogate escape |
| `invalid_json` | Malformed/unprocessable JSON, including a BOM, or a non-object root |
| `duplicate_key` | An object repeats the same decoded key |
| `nonfinite_number` | NaN, infinity, or a float literal that overflows to infinity |
| `invalid_configuration` | The parsed object or source-supplied configuration fails the existing inspection-domain contract |
| `identity_mismatch` | The loaded configuration's ID or revision differs from the validated query |

These controlled configuration errors do not put submitted values, key names, paths, or raw validation details into their public message or structured context. The adapter and service do not log input. `raise ... from None` suppresses the original exception chain in normal formatted tracebacks; Python's internal exception context and debugger locals are not erased and must not be exposed to clients.

### Local Filesystem Trust Boundary

The loader is an explicit local engineering interface, not an arbitrary-path upload interface. The HTTP route never supplies a client-selected path to it. Symlinks are followed if their target is a regular file; there is no allowed-directory sandbox. The path and its containing filesystem must be trusted. Checking the path and then its opened handle is not race-free: a hostile file replacement can still occur between operations, including a replacement that blocks at open. Concurrent edits are not an atomic snapshot. Publishing files atomically, provenance, path containment, snapshotting, and any future untrusted ingestion boundary need separate design before deployment.

## Read-Only Configuration Service

`src/plantguard_uav/repositories/inspection_configuration.py` declares `InspectionConfigurationSource`, a `Protocol` requiring a synchronous `load() -> InspectionFlightConfiguration` method. A protocol describes what a source must provide without tying the service to files or a database. This interface introduces no database storage.

`FileInspectionConfigurationSource` in the existing adapter implements that interface structurally: it provides the required method without needing to inherit from the protocol. Its constructor stores one caller-supplied trusted `Path` without opening it. Each `load()` call delegates to the existing bounded file loader, reads current contents, and propagates its controlled errors unchanged. It neither caches a successful result nor searches for another file after a failure. Relative paths retain the loader's call-time working-directory behavior; callers should supply absolute paths when location must remain stable.

`src/plantguard_uav/services/inspection_configuration.py` supplies:

- `GetInspectionConfigurationQuery`: required `configuration_id` and `configuration_version`, plus the existing default `schema_version="1.0"`. Identifiers must be nonblank strings; surrounding whitespace is removed. Unknown fields and unsupported schemas are rejected. The query is frozen, copied updates are validated, and existing instances are revalidated using a local setting rather than changing the shared model base.
- `GetInspectionConfigurationService(source)`: receives its source from the caller instead of choosing a path itself. `execute(query)` revalidates the query before any source access, calls `source.load()` once, revalidates the returned object with `InspectionFlightConfiguration`, and then compares the ID and revision to the query. Only a matching validated configuration is returned.

The source interface is exported from `plantguard_uav.repositories`; the query and service are exported from `plantguard_uav.services`. A caller supplies `path`, `expected_id`, and `expected_revision` explicitly:

```python
from plantguard_uav.adapters.inspection_configuration import FileInspectionConfigurationSource
from plantguard_uav.services import (
    GetInspectionConfigurationQuery,
    GetInspectionConfigurationService,
)

source = FileInspectionConfigurationSource(path)
service = GetInspectionConfigurationService(source)
query = GetInspectionConfigurationQuery(
    configuration_id=expected_id,
    configuration_version=expected_revision,
)
configuration = service.execute(query)
```

The query never determines a filesystem path. This source serves one configured file; it is not a catalogue, registry, or search facility. Identity comparison is case-sensitive equality after the existing whitespace normalization, with no revision ordering, implicit active profile, or "latest" fallback.

Invalid queries raise Pydantic `ValidationError` before reading the source. A source result that fails domain revalidation becomes a safe `InspectionConfigurationError` with reason `invalid_configuration`. A mismatched ID or revision becomes reason `identity_mismatch`; requested and returned identifiers are not included in its public message or context. Existing controlled source errors propagate unchanged. Unexpected programming errors are not hidden or converted into a fallback configuration. As with the domain models, machine-readable Pydantic validation details can contain inputs and must not be exposed indiscriminately.

The service and file source remain synchronous Python components independent of HTTP. The route described below wires them together without changing their validation behavior. There is no application-startup file read, database operation, or mission integration. Revalidation returns a validated value rather than promising the same Python object identity as the source result. Neither the source nor the service writes to files, changes configuration values, or approves flight.

### Identity Checking Is Not Snapshotting

Matching IDs and revisions establishes only that the returned metadata matches the request. A file edited without changing its ID and revision will still load if its new contents satisfy the contract; repeated reads will observe the new values. Content digests, provenance, revision uniqueness, immutable snapshots, and binding a configuration to a particular field or mission remain separate future work.

## Development/Testing HTTP Access

`GET /api/v1/inspection-configuration` requires query parameters `configuration_id` and `configuration_version`. They use the existing nonblank-string contract, including outer-whitespace normalization, and the result is the existing `InspectionFlightConfiguration` JSON model. URL-encode reserved characters when constructing requests. Identifiers select no path and have no special "latest" interpretation; unrelated query parameters are ignored rather than forwarded to the source.

### Explicit Server Wiring

The app factory accepts a new optional, keyword-only `inspection_configuration_source` argument. It stores that reference per app instance without calling `load()`. A trusted local Python entry point can wire a caller-chosen absolute `Path` named `trusted_configuration_path` as follows:

```python
import uvicorn

from plantguard_uav.adapters.inspection_configuration import FileInspectionConfigurationSource
from plantguard_uav.config import load_settings
from plantguard_uav.main import create_app

settings = load_settings()
app = create_app(
    settings,
    inspection_configuration_source=FileInspectionConfigurationSource(trusted_configuration_path),
)
uvicorn.run(app, host="127.0.0.1", port=settings.api.port)
```

`trusted_configuration_path` must be supplied by that entry point as a `pathlib.Path`, not taken from an HTTP request. The example does not create a preset file or choose operational values. The configured application environment must be `development` or `testing`; passing a source does not override the production exclusion. Existing defaults, YAML settings, environment-variable allowlist, and CLI behavior are unchanged. In particular, the normal `plantguard-uav` command supplies no inspection source, so valid requests to this endpoint receive `503` in development/testing until explicit programmatic wiring is provided.

### Request Flow and Responses

1. The dependency retrieves the optional source from application state without file I/O or a missing-source exception.
2. FastAPI validates both query identifiers before executing the route. Missing/blank identifiers receive the existing safe `422` response even when no source is configured.
3. The synchronous route creates the existing query and checks whether a source was supplied. If absent, it raises `InspectionConfigurationUnavailableError`, a `ConfigurationError` subclass with status `503`, the fixed message `Inspection configuration source is not configured.`, and controlled context reason `source_not_configured`. No retry time is invented.
4. With a source present, the route invokes `GetInspectionConfigurationService`, which reads fresh contents, revalidates the configuration, and verifies both identifiers.
5. A successful response is `200` with the validated JSON model. Existing file, parser, domain, and identity-mismatch failures remain safe `500` / `configuration_error` responses. Unexpected faults use the existing generic `500` / `internal_server_error` envelope with an error ID.

The route is declared with normal `def`, so synchronous service/file work executes in FastAPI's worker thread rather than directly in the asynchronous event loop. A supplied source may be called concurrently by different requests; custom source implementations must support independent concurrent reads. The built-in file source retains only its path and opens a separate file handle per load. API construction and startup never load this file. The route opens no database transaction. Process/database readiness checks remain independent of the optional configuration source; passing readiness does not promise this endpoint can load a profile.

The API reuses the existing error handlers and envelope. Success and handled `422`, `500`, and `503` responses include `Cache-Control: no-store`. Ordinary framework route-not-found `404` and method-not-allowed `405` responses are unchanged. Only `GET` is provided; there are no upload or mutation operations. Known loader/service failures do not put raw source paths, contents, or identifiers in public errors or controlled application-error context. The existing unexpected-error handler retains internal tracebacks, and external/access logs may include query strings: this is not a global log-redaction guarantee, and identifiers must not carry secrets.

### Exposure Boundary

The router is registered only for `development` and `testing`. Production omits it from the route table and generated schema even if the factory receives a source; a request gets the ordinary `404` without calling that source. The default production-configured Docker image therefore does not expose it.

Environment gating is not authentication or authorization. Keep development/testing servers local and unexposed. Operator authorization, production configuration access, durable snapshot binding, and qualified flight use remain future work. This endpoint neither chooses a profile for a mission nor persists a selection, modifies the source, or commands the drone.

## Validation Does Not Establish Flight Readiness

Acceptance by these models only proves the declared input structure and numeric relationships. It does not resolve or approve:

- battery policy or energy reserve;
- vehicle, camera, crop, or model compatibility;
- route geometry, terrain clearance, or obstacle/canopy clearance;
- hardware, weather, or operating-limit checks;
- operator authorization or safety-review provenance;
- complete mission configuration and immutable snapshot persistence.

Later mission creation and safety components must supply and validate those requirements. No flight-ready flag or approval state is added by these models.

## Source Contracts and Verification

The field-input list in [Data and Decision Contracts](data_and_decision_contracts.md) establishes survey/revisit AGL altitude, speed, overlap, the nominal operating category, and the separate battery-policy requirement. The lower-altitude revisit behavior is described in [Product Requirements](product_requirements.md). [V1 Scope Baseline](v1_scope_baseline.md) explicitly leaves actual flight values unresolved. The [Safety and Failure Policy](safety_and_failure_policy.md) retains independent authority over flight acceptance.

`tests/unit/domain/test_inspection_configuration.py` verifies required inputs, numeric bounds, rejected coercions, schema/environment rules, nested validation, immutability, copied updates, and JSON round trips. Its data is synthetic and must not be promoted into an operational profile.

`tests/unit/adapters/test_inspection_configuration_json.py` verifies the bytes parser, size/encoding/JSON defenses, domain-validation handoff, immutable results, and safe errors. `tests/unit/adapters/test_inspection_configuration_file.py` verifies explicit read-only file loading, bounded reads, handle cleanup, regular-file checks, current-file freshness, and controlled I/O failures. Both use synthetic data only.

`tests/unit/services/test_inspection_configuration_selection.py` verifies strict queries, source-result revalidation, exact identity matching, fresh reads, and error behavior using injected test sources. `tests/unit/adapters/test_inspection_configuration_source.py` verifies the file-source wrapper and the complete file-to-service path using synthetic temporary files, including changed or missing files after an earlier success.

`tests/api/test_inspection_configuration_api.py` verifies transport validation, responses, source wiring, worker-thread execution, safe failures, API documentation, and production exclusion. `tests/integration/test_inspection_configuration_api_flow.py` exercises the complete HTTP-to-file path with synthetic temporary inputs, checking freshness, unchanged files, and failure behavior after earlier successes.
