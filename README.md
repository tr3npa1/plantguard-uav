# PlantGuard UAV

PlantGuard UAV is a local-first crop-monitoring system that combines a PX4-compatible drone, RGB imagery, automated field-sector coverage, plant-health screening, and mandatory same-flight revisits of suspicious sites.

The repository is currently in its application-foundation stage. The production-v1 scope and system contracts are documented, and the first production-style API process now provides validated configuration, structured logging, safe errors, database migrations, transaction management, and process health endpoints. Flight control, image processing, inference, mapping, and the operator dashboard will be implemented incrementally.

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
