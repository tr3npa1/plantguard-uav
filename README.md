# PlantGuard UAV

PlantGuard UAV is a local-first crop-monitoring system that combines a PX4-compatible drone, RGB imagery, automated field-sector coverage, plant-health screening, and mandatory same-flight revisits of suspicious sites.

The repository is currently in its application-foundation stage. The production-v1 scope and system contracts are documented, and the first production-style API process now provides validated configuration, structured logging, safe errors, database migrations, transaction management, and process health endpoints. Read-only saved-field and inspection-configuration APIs are available in development and testing; configuration retrieval requires explicit server-side source wiring. Flight control, image processing, inference, mapping, and the operator dashboard will be implemented incrementally.

## Production-v1 Boundary

The first production release targets:

- one PX4-compatible drone;
- one field sector per mission;
- RGB imagery only;
- one qualified crop or crop family and a limited disease set;
- dry daylight operation;
- automatic coverage with approved exclusion zones;
- a local ground-station-first runtime;
- mandatory same-flight revisits when suspicious sites are detected.

Spraying, swarms, cloud-dependent operation, custom routes, degraded-weather operation, and automatic multi-flight stitching are outside production v1.

## Prerequisites

- Python 3.12
- Git
- Docker, when validating the container build

Python 3.13 and 3.14 are not currently supported by this project. Use Python 3.12 even if a newer interpreter is installed on the machine.

## Local Setup on Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,test]"
```

Database support is part of the production application and is installed by the command above. Install only the other additional capabilities needed for the work being performed. For example:

```powershell
python -m pip install -e ".[flight]"
python -m pip install -e ".[geospatial,vision]"
```

Prepare or update the local database before starting the API:

```powershell
alembic upgrade head
```

## Run the Local API

```powershell
plantguard-uav
```

The command starts a blocking local server at `http://127.0.0.1:8000`. Press `Ctrl+C` to stop it.

While the server is running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

`/health/live` proves that the HTTP process is answering. `/health/ready` additionally checks that the database can be reached and is at the expected migration revision. It does not claim that a drone, camera, weather condition, route, or mission is flight-ready.

## Saved-Field Read API

### Discover Saved Fields and Sectors

In development or testing, list saved field-sector choices before requesting their full definitions:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/fields?limit=20&offset=0"
```

`limit` defaults to `20` and must be between `1` and `100`. `offset` defaults to `0` and must be between `0` and `9223372036854775807` (the database's supported signed-integer maximum). Invalid pagination returns the safe `422` validation-error envelope before opening a database transaction.

The versioned response contains `items`, `limit`, `offset`, `has_more`, and `schema_version`. Each item contains `field_id`, `sector_id`, `field_name`, `crop_type`, `field_version`, and `schema_version`. One item represents one saved field-sector pair; a field with multiple sectors can appear multiple times. Both page and item schema versions are `"1.0"`.

Rows are ordered by `field_id`, then `sector_id`, using database text ordering. The query reads only summary columns and at most `limit + 1` rows; the extra row determines `has_more` and is excluded from `items`. To continue when `has_more` is true, request the same limit with `offset` increased by `limit`. No total-count query is performed.

An empty database or an offset beyond the last record returns `200` with `items: []` and `has_more: false`. Database failures and invalid fetched summary metadata return a safe `500` persistence error, including when invalid metadata is encountered in the lookahead row. Persisted identifiers that would change during normalization are rejected rather than advertised under a different lookup key.

Each request uses a separate transaction, finishes it before returning success, and sends `Cache-Control: no-store`. This is offset pagination over fresh reads, not a fixed snapshot: inserts, deletions, or changes between requests can shift page contents, so clients may need to refresh from offset zero. Large offsets can require the database to scan skipped entries; this catalogue does not promise constant-time deep pagination.

Catalogue items omit geometry and do not certify geometry validity, mission completeness, or flight readiness. Use an item's exact `field_id` and `sector_id` with the detail endpoint below to retrieve the validated saved definition. The catalogue does not group sectors into whole-field records and does not implement search, field creation/import, or operator selection.

### Retrieve One Saved Definition

In development or testing, request one saved field/sector pair:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/fields/definition?field_id=field-001&sector_id=sector-001"
```

Both query parameters are required, are treated as strings, and must contain a non-whitespace character. Leading and trailing whitespace is removed according to the existing identifier contract. Percent-encode reserved characters when constructing a URL; client libraries can encode values passed through their query-parameter options.

A successful response contains `field_id`, `sector_id`, `field_name`, `crop_type`, `field_boundary`, `sector_boundary`, `home_location`, `exclusion_zones`, `field_version`, and `schema_version`. Geometry uses the existing GeoJSON contracts with longitude before latitude; `schema_version` is `"1.0"`. Responses use `Cache-Control: no-store`, and every lookup opens its own transaction and reads the database again. The transaction finishes before a success response is returned.

| Status | Meaning |
| --- | --- |
| `200` | The validated saved definition was found. |
| `404` / `not_found` | That exact field/sector pair does not exist. |
| `422` / `validation_error` | A required identifier is missing or blank. |
| `500` / `persistence_error` | A database operation failed or stored data failed validation. |
| `500` / `internal_server_error` | An unexpected server error occurred; the response includes an error ID. |

Errors use an `error` object containing `code` and `message`, with `error_id` on unexpected errors. Request-validation responses omit submitted values and internal validation details. Application error responses also carry `Cache-Control: no-store`.

Apply the database migrations before use. Migrations create the table without adding sample fields, and a field-creation/import API has not been implemented. A newly migrated empty database therefore returns `404` for the example identifiers. Integration tests insert their own records into isolated temporary databases.

Both field endpoints only retrieve saved data. They do not persist an operator selection, emit a selection event, create a mission, authorize an operator, or establish flight readiness. Operator authentication and authorization remain required before production field access. For that reason, the field router is registered only in `development` and `testing`; `production` does not register it and returns the ordinary route-not-found `404`. Keep development/testing servers local and unexposed. The Docker image uses production configuration, so both field endpoints are unavailable there by default. Disabling interactive documentation alone is not access control.

## Inspection-Configuration Read API

In development or testing, a server with an explicitly wired configuration source supports:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/inspection-configuration?configuration_id=your-profile-id&configuration_version=your-profile-revision"
```

Replace both example identifiers with the expected ID and revision from your selected input. Both are required nonblank strings. Outer whitespace is trimmed, then comparison is case-sensitive; revisions are opaque identifiers, not a request for the latest profile. Reserved URL characters must be encoded. The response is the existing `InspectionFlightConfiguration`: identifiers, operating category, survey/revisit parameters, and schema versions. It is not a complete mission snapshot or flight approval.

The file path is chosen only in trusted server code, by passing `inspection_configuration_source=FileInspectionConfigurationSource(path)` to `create_app`. HTTP identifiers never become paths. See [Inspection Flight Configuration](docs/inspection_configuration.md#developmenttesting-http-access) for the wiring example and detailed behavior. No source is auto-discovered: the normal `plantguard-uav` command currently supplies none, so valid configuration requests return `503` until a source is explicitly wired through a Python entry point. Application YAML settings, environment-variable rules, and the CLI are unchanged.

| Status | Meaning |
| --- | --- |
| `200` | Fresh configuration was validated and its ID/revision matched. |
| `422` / `validation_error` | A required identifier is missing or blank; no source file is read, even if no source is configured. |
| `503` / `configuration_error` | This app instance has no configuration source wired. |
| `500` / `configuration_error` | The selected file could not be loaded/validated, or its ID/revision did not match. |
| `500` / `internal_server_error` | An unexpected error occurred; the generic response contains an error ID. |
| `404` in production | The route is not registered, even when a source was supplied to the app factory. |

Success and handled validation/application/unexpected-error responses include `Cache-Control: no-store`. Ordinary framework `404` and `405` responses are unchanged. Requests do not open database transactions or write files. Each successful read uses current contents, not a cache; matching metadata does not guarantee immutable contents. The synchronous route runs file loading in a worker thread. Neither app construction nor startup reads the source. Process/database readiness checks do not verify this optional source.

Keep this unauthenticated development/testing endpoint local and unexposed. It provides no file upload, configuration editor, profile catalogue, mission creation, or flight control. The production-configured Docker image does not expose it. Known configuration failures do not expose source paths or contents in their public error envelope; access logs and unexpected-exception traces are not a general secret-redaction boundary, so identifiers must not be secrets and operational logs require protection.

## Database Migrations

Alembic owns production schema changes. The API checks the schema revision but never upgrades or downgrades it automatically.

```powershell
alembic upgrade head
alembic current
alembic downgrade base
```

`upgrade head` applies every pending migration. `current` reports the revision used by the selected database. `downgrade base` is included for development verification; before a destructive production downgrade or migration, stop writers and take a verified backup.

The initial SQLite database is stored at `data/plantguard-uav.sqlite3`. SQLite is the local-first implementation, while the database boundary leaves room for a server database later. Application code must open transactions through the shared runtime, must not share an `AsyncSession` between concurrent tasks, and must not call `Base.metadata.create_all()` during production startup.

Interactive API documentation is available at `http://127.0.0.1:8000/docs` in development. Documentation and the OpenAPI schema are disabled when `PLANTGUARD_ENVIRONMENT=production`.

## Quality Checks

```powershell
ruff format --check .
ruff check .
mypy
pytest
pytest --cov=plantguard_uav --cov-report=term-missing
python -m build
```

Run these checks from the activated Python 3.12 virtual environment.

## Docker

Build the production-configured API image, prepare its persistent database volume, and then run it:

```powershell
docker build -t plantguard-uav:dev .
docker volume create plantguard-uav-data
docker run --rm --mount source=plantguard-uav-data,target=/app/data --entrypoint alembic plantguard-uav:dev upgrade head
docker run --rm -p 8000:8000 --mount source=plantguard-uav-data,target=/app/data plantguard-uav:dev
```

The image is built in two stages. Dependency wheels and build tools remain in the builder stage, while the final runtime installs from the wheelhouse, runs as a non-root user, binds on port 8000, uses JSON logs, and contains the version-controlled default configuration and migrations. `/app/data` is writable by the application user and backed by the named volume. Migration remains an explicit operator/deployment action instead of an API startup side effect.

## Repository Layout

```text
plantguard-uav/
|-- src/plantguard_uav/       Installable application package
|   |-- adapters/vehicle/     PX4 and future vehicle adapters
|   |-- api/routes/           Mission and field HTTP interfaces
|   |-- autonomy/             Route execution and autonomy logic
|   |-- classification/       Disease-classification components
|   |-- data/                 Application data contracts and transforms
|   |-- db/                   Database configuration and tables
|   |-- detection/            Plant and suspicious-site detection
|   |-- domain/               Core states and domain models
|   |-- mapping/              Coverage and map generation
|   |-- mission/              Mission-specific coordination logic
|   |-- repositories/         Persistence interfaces and implementations
|   |-- services/             Application orchestration services
|   `-- simulation/           Simulation helpers
|-- configs/                  Version-controlled default configuration
|-- data/                     Local raw and processed datasets
|-- docs/                     Product, architecture, and safety contracts
|-- migrations/               Database migrations
|-- models/                   Local model artifacts
|-- tests/                    Unit, API, repository, integration, and E2E tests
`-- artifacts/                Generated reports, logs, and test evidence
```

Generated datasets, models, logs, local databases, secrets, and test artifacts are intentionally excluded from Git.

## Configuration

Version-controlled defaults live in `configs/default.yaml`, with an identical copy packaged inside the installable wheel as a fallback. A repository or deployment-local file is preferred, while the packaged fallback lets the installed command start from another working directory. Configuration priority, from highest to lowest, is:

1. operating-system environment variables;
2. values in a local `.env` file;
3. `configs/default.yaml`;
4. defaults written in the Python settings models.

Copy `.env.example` to `.env` only when local overrides are needed. Nested settings use a double underscore, such as `PLANTGUARD_API__HOST`, `PLANTGUARD_DATABASE__URL`, and `PLANTGUARD_DATABASE__CONNECT_TIMEOUT_SECONDS`. Unknown YAML keys, unknown `PLANTGUARD_*` variables, and invalid values stop startup instead of being silently accepted.

Never commit `.env`, put real credentials in `.env.example`, or interpolate secrets into a log message. Structured fields with names such as `password`, `token`, `api_key`, `authorization`, `database_url`, and `dsn` are redacted before logs are rendered.

## Documentation

The authoritative production scope begins with:

- `docs/v1_scope_baseline.md`
- `docs/product_requirements.md`
- `docs/system_architecture.md`
- `docs/safety_and_failure_policy.md`
- `docs/verification_and_acceptance_plan.md`

Review these contracts before changing mission, safety, flight, image, or decision behavior.
