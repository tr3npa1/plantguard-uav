"""Exercise saved-field HTTP reads against a real, migrated temporary database."""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import URL, event
from sqlalchemy.ext.asyncio import AsyncSession

from plantguard_uav.config import Settings, settings_from_values
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.domain import GeoJsonPoint, GeoJsonPolygon, SavedFieldDefinition
from plantguard_uav.main import create_app

pytestmark = pytest.mark.integration

_ENDPOINT = "/api/v1/fields/definition"
_CATALOGUE_ENDPOINT = "/api/v1/fields"
_PERSISTENCE_ERROR = {
    "error": {
        "code": "persistence_error",
        "message": "Persistent storage operation could not be completed.",
    },
}


@dataclass(frozen=True)
class _FieldApi:
    client: TestClient
    database_path: Path
    runtime: DatabaseRuntime


def _settings(database_path: Path) -> Settings:
    return settings_from_values(
        {
            "environment": "testing",
            "database": {
                "url": f"sqlite+aiosqlite:///{database_path.as_posix()}",
                "connect_timeout_seconds": 1,
            },
        },
    )


@pytest.fixture
def field_api(project_root: Path, tmp_path: Path) -> Iterator[_FieldApi]:
    database_path = tmp_path / "field-api.sqlite3"
    migration_config = Config(str(project_root / "alembic.ini"))
    migration_config.set_main_option("script_location", str(project_root / "migrations"))
    database_url = URL.create(
        "sqlite+aiosqlite",
        database=str(database_path.resolve()),
    ).render_as_string(hide_password=False)
    migration_config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(migration_config, "head")

    settings = _settings(database_path)
    runtime = DatabaseRuntime.from_settings(settings.database)
    with TestClient(create_app(settings, database_runtime=runtime)) as client:
        yield _FieldApi(client=client, database_path=database_path, runtime=runtime)


def _polygon(longitude_offset: float = 0.0) -> GeoJsonPolygon:
    return GeoJsonPolygon(
        coordinates=(
            (
                (77.0 + longitude_offset, 28.0),
                (77.2 + longitude_offset, 28.0),
                (77.2 + longitude_offset, 28.2),
                (77.0 + longitude_offset, 28.0),
            ),
        ),
    )


def _definition(
    *,
    field_id: str = "field-alpha",
    sector_id: str = "sector-north",
) -> SavedFieldDefinition:
    return SavedFieldDefinition(
        field_id=field_id,
        sector_id=sector_id,
        field_name="North Demonstration Field",
        crop_type="wheat",
        field_boundary=_polygon(),
        sector_boundary=_polygon(0.01),
        home_location=GeoJsonPoint(coordinates=(77.05, 28.05)),
        exclusion_zones=(_polygon(0.02), _polygon(0.04)),
        field_version="field-version-7",
    )


def _store(database_path: Path, *definitions: SavedFieldDefinition) -> None:
    # Setup uses a separate connection; the HTTP request performs the async read.
    with closing(sqlite3.connect(database_path)) as connection, connection:
        for definition in definitions:
            connection.execute(
                "INSERT INTO saved_field_definitions "
                "(field_id, sector_id, field_name, crop_type, field_boundary, "
                "sector_boundary, home_location, exclusion_zones, field_version, schema_version) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    definition.field_id,
                    definition.sector_id,
                    definition.field_name,
                    definition.crop_type,
                    definition.field_boundary.model_dump_json(),
                    definition.sector_boundary.model_dump_json(),
                    definition.home_location.model_dump_json(),
                    json.dumps(
                        [zone.model_dump(mode="json") for zone in definition.exclusion_zones],
                    ),
                    definition.field_version,
                    definition.schema_version,
                ),
            )


def _snapshot(database_path: Path) -> list[str]:
    with closing(sqlite3.connect(database_path)) as connection, connection:
        return list(connection.iterdump())


def test_http_returns_the_exact_complete_saved_field_sector(field_api: _FieldApi) -> None:
    expected = _definition()
    _store(
        field_api.database_path,
        expected,
        _definition(sector_id="sector-south"),
        _definition(field_id="field-beta"),
    )
    before = _snapshot(field_api.database_path)

    response = field_api.client.get(
        _ENDPOINT,
        params={"field_id": expected.field_id, "sector_id": expected.sector_id},
    )

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "no-store"
    assert _snapshot(field_api.database_path) == before


@pytest.mark.parametrize(
    ("field_id", "sector_id"),
    [
        ("field/a?b#c&d=e+f%20", "sector/one?x=1&y=2"),
        ("field-खेत", "sector-उत्तर"),
        ("field-' OR 1=1 --", 'sector-"; DROP TABLE saved_field_definitions; --'),
    ],
)
def test_http_preserves_opaque_identifiers_and_parameterizes_database_reads(
    field_api: _FieldApi,
    field_id: str,
    sector_id: str,
) -> None:
    expected = _definition(field_id=field_id, sector_id=sector_id)
    _store(field_api.database_path, _definition(), expected)
    before = _snapshot(field_api.database_path)

    response = field_api.client.get(
        _ENDPOINT,
        params={"field_id": field_id, "sector_id": sector_id},
    )

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")
    assert _snapshot(field_api.database_path) == before


@pytest.mark.parametrize(
    ("field_id", "sector_id"),
    [("unknown-field", "sector-north"), ("field-alpha", "unknown-sector")],
)
def test_http_returns_not_found_without_mutating_existing_records(
    field_api: _FieldApi,
    field_id: str,
    sector_id: str,
) -> None:
    _store(field_api.database_path, _definition())
    before = _snapshot(field_api.database_path)

    response = field_api.client.get(
        _ENDPOINT,
        params={"field_id": field_id, "sector_id": sector_id},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "The requested saved field sector was not found.",
        },
    }
    assert _snapshot(field_api.database_path) == before


def test_each_http_request_reads_a_fresh_committed_definition(field_api: _FieldApi) -> None:
    expected = _definition()
    _store(field_api.database_path, expected)
    params = {"field_id": expected.field_id, "sector_id": expected.sector_id}

    first = field_api.client.get(_ENDPOINT, params=params)
    with closing(sqlite3.connect(field_api.database_path)) as connection, connection:
        connection.execute(
            "UPDATE saved_field_definitions SET field_version = ?, field_name = ? "
            "WHERE field_id = ? AND sector_id = ?",
            (
                "field-version-8",
                "Updated Demonstration Field",
                expected.field_id,
                expected.sector_id,
            ),
        )
    after_update = _snapshot(field_api.database_path)
    second = field_api.client.get(_ENDPOINT, params=params)

    assert first.status_code == 200
    assert first.json() == expected.model_dump(mode="json")
    assert second.status_code == 200
    assert second.json() == expected.model_copy(
        update={"field_version": "field-version-8", "field_name": "Updated Demonstration Field"},
    ).model_dump(mode="json")
    assert _snapshot(field_api.database_path) == after_update


def test_http_uses_distinct_sessions_and_returns_connections_after_each_request(
    field_api: _FieldApi,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _definition()
    _store(field_api.database_path, expected)
    sessions: list[AsyncSession] = []
    pool_events: list[str] = []
    transaction = field_api.runtime.transaction

    @asynccontextmanager
    async def traced_transaction() -> AsyncIterator[AsyncSession]:
        async with transaction() as session:
            sessions.append(session)
            yield session

    def checked_out(
        _connection: object,
        _record: object,
        _proxy: object,
    ) -> None:
        pool_events.append("checkout")

    def checked_in(_connection: object, _record: object) -> None:
        pool_events.append("checkin")

    monkeypatch.setattr(field_api.runtime, "transaction", traced_transaction)
    event.listen(field_api.runtime.engine.sync_engine, "checkout", checked_out)
    event.listen(field_api.runtime.engine.sync_engine, "checkin", checked_in)
    params = {"field_id": expected.field_id, "sector_id": expected.sector_id}

    first = field_api.client.get(_ENDPOINT, params=params)
    assert first.status_code == 200
    assert pool_events == ["checkout", "checkin"]
    assert len(sessions) == 1
    assert sessions[0].in_transaction() is False

    second = field_api.client.get(_ENDPOINT, params=params)
    assert second.status_code == 200
    assert pool_events == ["checkout", "checkin", "checkout", "checkin"]
    assert len(sessions) == 2
    assert sessions[0] is not sessions[1]
    assert sessions[1].in_transaction() is False


@pytest.mark.parametrize(
    "stored_boundary",
    [
        json.dumps(
            {
                "type": "Polygon",
                "coordinates": [[[999, 28], [77.2, 28], [77.2, 28.2], [999, 28]]],
                "private_marker": "private-corrupt-field-value",
            },
        ),
        "private-corrupt-field-value-not-json",
        "null",
    ],
)
def test_http_hides_corrupt_persisted_geometry_and_json(
    field_api: _FieldApi,
    stored_boundary: str,
) -> None:
    expected = _definition()
    _store(field_api.database_path, expected)
    with closing(sqlite3.connect(field_api.database_path)) as connection, connection:
        connection.execute(
            "UPDATE saved_field_definitions SET field_boundary = ?",
            (stored_boundary,),
        )
    before = _snapshot(field_api.database_path)

    response = field_api.client.get(
        _ENDPOINT,
        params={"field_id": expected.field_id, "sector_id": expected.sector_id},
    )

    assert response.status_code == 500
    assert response.json() == _PERSISTENCE_ERROR
    assert "private-corrupt" not in response.text
    assert str(field_api.database_path) not in response.text
    assert _snapshot(field_api.database_path) == before


def test_http_hides_sql_details_when_the_saved_field_table_is_missing(
    field_api: _FieldApi,
) -> None:
    with closing(sqlite3.connect(field_api.database_path)) as connection, connection:
        connection.execute("DROP TABLE saved_field_definitions")

    response = field_api.client.get(
        _ENDPOINT,
        params={"field_id": "field-alpha", "sector_id": "sector-north"},
    )

    assert response.status_code == 500
    assert response.json() == _PERSISTENCE_ERROR
    assert "saved_field_definitions" not in response.text
    assert "SELECT" not in response.text
    assert str(field_api.database_path) not in response.text


def test_http_hides_storage_location_when_database_connection_fails(tmp_path: Path) -> None:
    database_path = tmp_path / "private-missing-directory" / "private-storage.sqlite3"
    settings = _settings(database_path)
    with TestClient(create_app(settings)) as client:
        response = client.get(
            _ENDPOINT,
            params={"field_id": "field-alpha", "sector_id": "sector-north"},
        )

    assert response.status_code == 500
    assert response.json() == _PERSISTENCE_ERROR
    assert "private-" not in response.text
    assert str(tmp_path) not in response.text
    assert database_path.parent.exists() is False


def _expected_summary(definition: SavedFieldDefinition) -> dict[str, str]:
    return {
        "field_id": definition.field_id,
        "sector_id": definition.sector_id,
        "field_name": definition.field_name,
        "crop_type": definition.crop_type,
        "field_version": definition.field_version,
        "schema_version": definition.schema_version,
    }


def test_catalogue_orders_field_sector_pairs_and_supports_discovery_then_detail(
    field_api: _FieldApi,
) -> None:
    first = _definition(field_id="field-alpha", sector_id="sector-north")
    second = _definition(field_id="field-alpha", sector_id="sector-south")
    third = _definition(field_id="field-beta", sector_id="sector-north")
    fourth = _definition(field_id="field-gamma", sector_id="sector-east")
    _store(field_api.database_path, fourth, second, third, first)
    before = _snapshot(field_api.database_path)

    page_one = field_api.client.get(_CATALOGUE_ENDPOINT, params={"limit": 2})
    page_two = field_api.client.get(_CATALOGUE_ENDPOINT, params={"limit": 2, "offset": 2})

    assert page_one.status_code == 200
    assert page_one.json() == {
        "items": [_expected_summary(first), _expected_summary(second)],
        "limit": 2,
        "offset": 0,
        "has_more": True,
        "schema_version": "1.0",
    }
    assert page_two.status_code == 200
    assert page_two.json() == {
        "items": [_expected_summary(third), _expected_summary(fourth)],
        "limit": 2,
        "offset": 2,
        "has_more": False,
        "schema_version": "1.0",
    }
    selected = page_one.json()["items"][1]
    detail = field_api.client.get(
        _ENDPOINT,
        params={"field_id": selected["field_id"], "sector_id": selected["sector_id"]},
    )
    assert detail.status_code == 200
    assert detail.json() == second.model_dump(mode="json")
    for response in (page_one, page_two, detail):
        assert response.headers["cache-control"] == "no-store"
    assert _snapshot(field_api.database_path) == before


@pytest.mark.parametrize("offset", [0, 1, 2**63 - 1])
def test_catalogue_empty_database_returns_a_valid_empty_page(
    field_api: _FieldApi,
    offset: int,
) -> None:
    before = _snapshot(field_api.database_path)

    response = field_api.client.get(_CATALOGUE_ENDPOINT, params={"offset": offset})

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "limit": 20,
        "offset": offset,
        "has_more": False,
        "schema_version": "1.0",
    }
    assert _snapshot(field_api.database_path) == before


@pytest.mark.parametrize("offset", [1, 10, 2**63 - 1])
def test_catalogue_offset_beyond_last_record_returns_an_empty_page(
    field_api: _FieldApi,
    offset: int,
) -> None:
    _store(field_api.database_path, _definition())

    response = field_api.client.get(_CATALOGUE_ENDPOINT, params={"limit": 1, "offset": offset})

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["offset"] == offset
    assert response.json()["has_more"] is False


def test_catalogue_each_page_reads_fresh_committed_metadata(field_api: _FieldApi) -> None:
    expected = _definition()
    _store(field_api.database_path, expected)

    first = field_api.client.get(_CATALOGUE_ENDPOINT)
    with closing(sqlite3.connect(field_api.database_path)) as connection, connection:
        connection.execute(
            "UPDATE saved_field_definitions SET field_version = ?, field_name = ? "
            "WHERE field_id = ? AND sector_id = ?",
            ("field-version-8", "Renamed Field", expected.field_id, expected.sector_id),
        )
    before_second = _snapshot(field_api.database_path)
    second = field_api.client.get(_CATALOGUE_ENDPOINT)

    assert first.status_code == 200
    assert first.json()["items"] == [_expected_summary(expected)]
    assert second.status_code == 200
    assert second.json()["items"] == [
        {
            **_expected_summary(expected),
            "field_version": "field-version-8",
            "field_name": "Renamed Field",
        },
    ]
    assert _snapshot(field_api.database_path) == before_second


def test_catalogue_uses_fresh_sessions_and_releases_connections_before_returning(
    field_api: _FieldApi,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _store(field_api.database_path, _definition())
    sessions: list[AsyncSession] = []
    pool_events: list[str] = []
    transaction = field_api.runtime.transaction

    @asynccontextmanager
    async def traced_transaction() -> AsyncIterator[AsyncSession]:
        async with transaction() as session:
            sessions.append(session)
            yield session

    def checked_out(_connection: object, _record: object, _proxy: object) -> None:
        pool_events.append("checkout")

    def checked_in(_connection: object, _record: object) -> None:
        pool_events.append("checkin")

    monkeypatch.setattr(field_api.runtime, "transaction", traced_transaction)
    event.listen(field_api.runtime.engine.sync_engine, "checkout", checked_out)
    event.listen(field_api.runtime.engine.sync_engine, "checkin", checked_in)

    first = field_api.client.get(_CATALOGUE_ENDPOINT)
    assert first.status_code == 200
    assert pool_events == ["checkout", "checkin"]
    assert len(sessions) == 1
    assert sessions[0].in_transaction() is False

    second = field_api.client.get(_CATALOGUE_ENDPOINT)
    assert second.status_code == 200
    assert pool_events == ["checkout", "checkin", "checkout", "checkin"]
    assert len(sessions) == 2
    assert sessions[0] is not sessions[1]
    assert sessions[1].in_transaction() is False


@pytest.mark.parametrize("invalid_sector", ["sector-north", "sector-south"])
def test_catalogue_rejects_invalid_summary_metadata_in_items_or_lookahead(
    field_api: _FieldApi,
    invalid_sector: str,
) -> None:
    _store(field_api.database_path, _definition(), _definition(sector_id="sector-south"))
    with closing(sqlite3.connect(field_api.database_path)) as connection, connection:
        # SQLite trim() strips spaces; our contract also rejects tabs and newlines.
        connection.execute(
            "UPDATE saved_field_definitions SET field_name = ? WHERE sector_id = ?",
            ("\t\n", invalid_sector),
        )
    before = _snapshot(field_api.database_path)

    response = field_api.client.get(_CATALOGUE_ENDPOINT, params={"limit": 1})

    assert response.status_code == 500
    assert response.json() == _PERSISTENCE_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert str(field_api.database_path) not in response.text
    assert _snapshot(field_api.database_path) == before


def test_catalogue_does_not_read_geometry_or_certify_detail_validity(field_api: _FieldApi) -> None:
    expected = _definition()
    _store(field_api.database_path, expected)
    with closing(sqlite3.connect(field_api.database_path)) as connection, connection:
        connection.execute(
            "UPDATE saved_field_definitions SET field_boundary = ?",
            ("private-invalid-geometry-json",),
        )
    before = _snapshot(field_api.database_path)

    catalogue = field_api.client.get(_CATALOGUE_ENDPOINT)
    detail = field_api.client.get(
        _ENDPOINT,
        params={"field_id": expected.field_id, "sector_id": expected.sector_id},
    )

    assert catalogue.status_code == 200
    assert catalogue.json()["items"] == [_expected_summary(expected)]
    assert detail.status_code == 500
    assert detail.json() == _PERSISTENCE_ERROR
    assert "private-invalid-geometry-json" not in catalogue.text
    assert "private-invalid-geometry-json" not in detail.text
    assert _snapshot(field_api.database_path) == before


def test_catalogue_database_failure_returns_a_safe_persistence_error(field_api: _FieldApi) -> None:
    with closing(sqlite3.connect(field_api.database_path)) as connection, connection:
        connection.execute("DROP TABLE saved_field_definitions")

    response = field_api.client.get(_CATALOGUE_ENDPOINT)

    assert response.status_code == 500
    assert response.json() == _PERSISTENCE_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert "saved_field_definitions" not in response.text
    assert "SELECT" not in response.text
    assert str(field_api.database_path) not in response.text
