from collections.abc import Callable
import json
from pathlib import Path
import sqlite3
from unittest.mock import AsyncMock

from alembic import command
from alembic.config import Config
from pydantic import SecretStr
import pytest
from sqlalchemy import URL, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from plantguard_uav.config import DatabaseSettings
from plantguard_uav.db import DatabaseRuntime, SavedFieldDefinitionRow
from plantguard_uav.domain import GeoJsonPoint, GeoJsonPolygon, SavedFieldDefinition
from plantguard_uav.domain.field import SavedFieldSummary
from plantguard_uav.errors import PersistenceError
from plantguard_uav.repositories import SqlAlchemyFieldDefinitionRepository
from plantguard_uav.services import GetFieldDefinitionQuery, GetFieldDefinitionService

pytestmark = pytest.mark.integration


def _migration_config(project_root: Path, database_path: Path) -> Config:
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    database_url = URL.create(
        "sqlite+aiosqlite",
        database=str(database_path.resolve()),
    ).render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@pytest.fixture
def migrated_database_path(project_root: Path, tmp_path: Path) -> Path:
    database_path = tmp_path / "repository.sqlite3"
    command.upgrade(_migration_config(project_root, database_path), "head")
    return database_path


def _runtime(database_path: Path) -> DatabaseRuntime:
    settings = DatabaseSettings(
        url=SecretStr(f"sqlite+aiosqlite:///{database_path.as_posix()}"),
        connect_timeout_seconds=1.0,
    )
    return DatabaseRuntime.from_settings(settings)


def _polygon(longitude_offset: float = 0.0) -> GeoJsonPolygon:
    return GeoJsonPolygon(
        coordinates=(
            (
                (77.0 + longitude_offset, 28.0),
                (77.2 + longitude_offset, 28.0),
                (77.2 + longitude_offset, 28.2),
                (77.0 + longitude_offset, 28.0),
            ),
        )
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


async def _store(runtime: DatabaseRuntime, *definitions: SavedFieldDefinition) -> None:
    async with runtime.transaction() as session:
        session.add_all(
            [
                SavedFieldDefinitionRow(**definition.model_dump(mode="json"))
                for definition in definitions
            ]
        )


async def _load(
    runtime: DatabaseRuntime,
    definition: SavedFieldDefinition,
) -> SavedFieldDefinition | None:
    async with runtime.transaction() as session:
        return await SqlAlchemyFieldDefinitionRepository(session).get_definition(
            field_id=definition.field_id,
            sector_id=definition.sector_id,
        )


async def test_migrated_repository_and_service_return_the_complete_definition(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    expected = _definition()
    try:
        await _store(runtime, expected)

        async with runtime.transaction() as session:
            repository = SqlAlchemyFieldDefinitionRepository(session)
            service = GetFieldDefinitionService(repository)
            actual = await service.execute(
                GetFieldDefinitionQuery(
                    field_id=expected.field_id,
                    sector_id=expected.sector_id,
                )
            )

        assert actual == expected
        assert len(actual.exclusion_zones) == 2
        assert actual.model_dump(mode="json")["field_boundary"]["coordinates"] == [
            [[77.0, 28.0], [77.2, 28.0], [77.2, 28.2], [77.0, 28.0]]
        ]
    finally:
        await runtime.dispose()


async def test_repository_matches_only_the_exact_parameterized_identifier_pair(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    normal = _definition()
    special = _definition(
        field_id="field-' OR 1=1 --",
        sector_id='sector-"; DROP TABLE saved_field_definitions; --',
    )
    try:
        await _store(runtime, normal, special)

        async with runtime.transaction() as session:
            repository = SqlAlchemyFieldDefinitionRepository(session)
            exact_special = await repository.get_definition(
                field_id=special.field_id,
                sector_id=special.sector_id,
            )
            similar_sector = await repository.get_definition(
                field_id=normal.field_id,
                sector_id="sector-north-extra",
            )
            similar_field = await repository.get_definition(
                field_id="field",
                sector_id=normal.sector_id,
            )

        assert exact_special == special
        assert similar_sector is None
        assert similar_field is None
    finally:
        await runtime.dispose()


def _corrupt_geometry(connection: sqlite3.Connection) -> str:
    private_value = "private-invalid-coordinate-999"
    geometry = {
        "type": "Polygon",
        "coordinates": [[[999, 28.0], [77.2, 28.0], [77.2, 28.2], [999, 28.0]]],
        "private_marker": private_value,
    }
    connection.execute(
        "UPDATE saved_field_definitions SET field_boundary = ?",
        (json.dumps(geometry),),
    )
    return private_value


def _corrupt_schema_version(connection: sqlite3.Connection) -> str:
    private_value = "private-schema-version-9.9"
    connection.execute("PRAGMA ignore_check_constraints = ON")
    connection.execute(
        "UPDATE saved_field_definitions SET schema_version = ?",
        (private_value,),
    )
    connection.execute("PRAGMA ignore_check_constraints = OFF")
    return private_value


def _corrupt_geometry_with_json_null(connection: sqlite3.Connection) -> str:
    connection.execute(
        "UPDATE saved_field_definitions SET field_boundary = ?",
        ("null",),
    )
    return "null"


def _corrupt_geometry_with_invalid_json(connection: sqlite3.Connection) -> str:
    private_value = "private-not-json"
    connection.execute(
        "UPDATE saved_field_definitions SET field_boundary = ?",
        (private_value,),
    )
    return private_value


@pytest.mark.parametrize(
    "corrupt",
    [
        _corrupt_geometry,
        _corrupt_schema_version,
        _corrupt_geometry_with_json_null,
        _corrupt_geometry_with_invalid_json,
    ],
)
async def test_corrupt_stored_values_raise_only_a_safe_persistence_error(
    migrated_database_path: Path,
    corrupt: Callable[[sqlite3.Connection], str],
) -> None:
    runtime = _runtime(migrated_database_path)
    definition = _definition()
    try:
        await _store(runtime, definition)
        with sqlite3.connect(migrated_database_path) as connection:
            private_value = corrupt(connection)

        with pytest.raises(PersistenceError, match="could not be completed") as error:
            await _load(runtime, definition)

        assert error.value.context == {
            "operation": "get_field_definition",
            "reason": "invalid_stored_data",
        }
        assert private_value not in error.value.public_message
        assert private_value not in repr(error.value.context)
    finally:
        await runtime.dispose()


async def test_next_request_observes_a_newly_committed_field_version(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    definition = _definition()
    try:
        await _store(runtime, definition)

        async with runtime.transaction() as session:
            first = await SqlAlchemyFieldDefinitionRepository(session).get_definition(
                field_id=definition.field_id,
                sector_id=definition.sector_id,
            )

        async with runtime.transaction() as session:
            await session.execute(
                update(SavedFieldDefinitionRow)
                .where(
                    SavedFieldDefinitionRow.field_id == definition.field_id,
                    SavedFieldDefinitionRow.sector_id == definition.sector_id,
                )
                .values(field_version="field-version-8")
            )

        async with runtime.transaction() as session:
            second = await SqlAlchemyFieldDefinitionRepository(session).get_definition(
                field_id=definition.field_id,
                sector_id=definition.sector_id,
            )

        assert first is not None
        assert first.field_version == "field-version-7"
        assert second is not None
        assert second.field_version == "field-version-8"
    finally:
        await runtime.dispose()


async def test_repository_never_commits_or_rolls_back_its_caller_owned_transaction(
    migrated_database_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(migrated_database_path)
    definition = _definition()
    try:
        await _store(runtime, definition)

        async with runtime.transaction() as session:
            commit = AsyncMock(side_effect=AssertionError("repository attempted to commit"))
            rollback = AsyncMock(side_effect=AssertionError("repository attempted to roll back"))
            monkeypatch.setattr(session, "commit", commit)
            monkeypatch.setattr(session, "rollback", rollback)

            actual = await SqlAlchemyFieldDefinitionRepository(session).get_definition(
                field_id=definition.field_id,
                sector_id=definition.sector_id,
            )

            assert actual == definition
            assert session.in_transaction() is True
            commit.assert_not_awaited()
            rollback.assert_not_awaited()
    finally:
        await runtime.dispose()


async def test_database_driver_errors_are_normalized_without_private_details() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = SQLAlchemyError("private database statement")
    repository = SqlAlchemyFieldDefinitionRepository(session)

    with pytest.raises(PersistenceError, match="could not be completed") as error:
        await repository.get_definition(field_id="field-alpha", sector_id="sector-north")

    assert error.value.context == {
        "operation": "get_field_definition",
        "reason": "database_error",
    }
    assert "private" not in error.value.public_message
    assert "private" not in repr(error.value.context)


def _summary(definition: SavedFieldDefinition) -> SavedFieldSummary:
    return SavedFieldSummary(
        field_id=definition.field_id,
        sector_id=definition.sector_id,
        field_name=definition.field_name,
        crop_type=definition.crop_type,
        field_version=definition.field_version,
        schema_version=definition.schema_version,
    )


async def _list_summaries(
    runtime: DatabaseRuntime,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[SavedFieldSummary, ...]:
    async with runtime.transaction() as session:
        return await SqlAlchemyFieldDefinitionRepository(session).list_summaries(
            limit=limit,
            offset=offset,
        )


async def test_catalogue_orders_by_both_field_and_sector_identifiers(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    expected = (
        _definition(field_id="field-alpha", sector_id="sector-east"),
        _definition(field_id="field-alpha", sector_id="sector-west"),
        _definition(field_id="field-beta", sector_id="sector-east"),
        _definition(field_id="field-beta", sector_id="sector-west"),
    )
    try:
        await _store(runtime, expected[3], expected[1], expected[2], expected[0])

        first = await _list_summaries(runtime, limit=2)
        second = await _list_summaries(runtime, limit=2, offset=2)
        repeated = await _list_summaries(runtime, limit=2)

        assert first == tuple(_summary(definition) for definition in expected[:2])
        assert second == tuple(_summary(definition) for definition in expected[2:])
        assert first + second == tuple(_summary(definition) for definition in expected)
        assert repeated == first
        assert {(item.field_id, item.sector_id) for item in first}.isdisjoint(
            (item.field_id, item.sector_id) for item in second
        )
    finally:
        await runtime.dispose()


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(1, 0), (2, 0), (2, 2), (2, 4), (100, 0), (101, 0), (2, 5), (2, 6), (2, 2**63 - 1)],
)
async def test_catalogue_applies_bounded_limit_and_offset(
    migrated_database_path: Path,
    limit: int,
    offset: int,
) -> None:
    runtime = _runtime(migrated_database_path)
    definitions = tuple(_definition(field_id=f"field-{index}") for index in range(5))
    try:
        await _store(runtime, *reversed(definitions))

        actual = await _list_summaries(runtime, limit=limit, offset=offset)

        assert actual == tuple(
            _summary(definition) for definition in definitions[offset : offset + limit]
        )
        assert len(actual) <= limit
    finally:
        await runtime.dispose()


async def test_catalogue_returns_an_empty_tuple_for_an_empty_database(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    try:
        assert await _list_summaries(runtime) == ()
    finally:
        await runtime.dispose()


async def test_catalogue_can_fetch_the_largest_page_and_its_lookahead_row(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    definitions = tuple(_definition(field_id=f"field-{index:03}") for index in range(102))
    try:
        await _store(runtime, *reversed(definitions))

        first = await _list_summaries(runtime, limit=101)
        remainder = await _list_summaries(runtime, limit=101, offset=101)

        assert len(first) == 101
        assert first == tuple(_summary(definition) for definition in definitions[:101])
        assert remainder == (_summary(definitions[101]),)
    finally:
        await runtime.dispose()


async def test_catalogue_does_not_load_or_validate_geometry_columns(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    definition = _definition()
    try:
        await _store(runtime, definition)
        with sqlite3.connect(migrated_database_path) as connection:
            connection.execute(
                "UPDATE saved_field_definitions "
                "SET field_boundary = ?, sector_boundary = ?, home_location = ?, exclusion_zones = ?",
                (
                    "invalid-field-json",
                    "invalid-sector-json",
                    "invalid-home-json",
                    "invalid-zones-json",
                ),
            )
            stored_before = connection.execute("SELECT * FROM saved_field_definitions").fetchall()

        actual = await _list_summaries(runtime)

        assert actual == (_summary(definition),)
        assert set(actual[0].model_dump()) == {
            "field_id",
            "sector_id",
            "field_name",
            "crop_type",
            "field_version",
            "schema_version",
        }
        with sqlite3.connect(migrated_database_path) as connection:
            stored_after = connection.execute("SELECT * FROM saved_field_definitions").fetchall()
        assert stored_after == stored_before
    finally:
        await runtime.dispose()


@pytest.mark.parametrize(
    ("column", "invalid_value"),
    [
        ("field_id", " "),
        ("sector_id", " "),
        ("field_name", " "),
        ("crop_type", " "),
        ("field_version", " "),
        ("schema_version", "private-invalid-schema"),
    ],
)
async def test_catalogue_rejects_invalid_stored_summary_metadata(
    migrated_database_path: Path,
    column: str,
    invalid_value: str,
) -> None:
    runtime = _runtime(migrated_database_path)
    try:
        await _store(runtime, _definition())
        with sqlite3.connect(migrated_database_path) as connection:
            connection.execute("PRAGMA ignore_check_constraints = ON")
            connection.execute(
                f"UPDATE saved_field_definitions SET {column} = ?",
                (invalid_value,),
            )
            connection.execute("PRAGMA ignore_check_constraints = OFF")

        with pytest.raises(PersistenceError, match="could not be completed") as error:
            await _list_summaries(runtime)

        assert error.value.context == {
            "operation": "list_field_summaries",
            "reason": "invalid_stored_data",
        }
        assert "private" not in error.value.public_message
        assert "private" not in repr(error.value.context)
    finally:
        await runtime.dispose()


@pytest.mark.parametrize(
    ("column", "padded_identifier"),
    [("field_id", " field-alpha "), ("sector_id", " sector-north ")],
)
async def test_catalogue_rejects_stored_keys_that_would_change_during_validation(
    migrated_database_path: Path,
    column: str,
    padded_identifier: str,
) -> None:
    runtime = _runtime(migrated_database_path)
    try:
        await _store(runtime, _definition())
        with sqlite3.connect(migrated_database_path) as connection:
            connection.execute(
                f"UPDATE saved_field_definitions SET {column} = ?",
                (padded_identifier,),
            )

        with pytest.raises(PersistenceError, match="could not be completed") as error:
            await _list_summaries(runtime)

        assert error.value.context == {
            "operation": "list_field_summaries",
            "reason": "invalid_stored_data",
        }
        assert padded_identifier not in error.value.public_message
        assert padded_identifier not in repr(error.value.context)
    finally:
        await runtime.dispose()


async def test_catalogue_preserves_canonical_opaque_keys_for_detail_lookup(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    definition = _definition(
        field_id="field-' OR 1=1 --/北",
        sector_id='sector-"; DROP TABLE saved_field_definitions; --/南',
    )
    try:
        await _store(runtime, definition)

        summaries = await _list_summaries(runtime)
        assert summaries == (_summary(definition),)

        async with runtime.transaction() as session:
            actual = await SqlAlchemyFieldDefinitionRepository(session).get_definition(
                field_id=summaries[0].field_id,
                sector_id=summaries[0].sector_id,
            )
        assert actual == definition
    finally:
        await runtime.dispose()


async def test_catalogue_validates_every_fetched_row_including_the_lookahead(
    migrated_database_path: Path,
) -> None:
    runtime = _runtime(migrated_database_path)
    first = _definition(field_id="field-alpha")
    second = _definition(field_id="field-beta")
    try:
        await _store(runtime, first, second)
        with sqlite3.connect(migrated_database_path) as connection:
            connection.execute("PRAGMA ignore_check_constraints = ON")
            connection.execute(
                "UPDATE saved_field_definitions SET field_name = ? WHERE field_id = ?",
                (" ", second.field_id),
            )
            connection.execute("PRAGMA ignore_check_constraints = OFF")

        assert await _list_summaries(runtime, limit=1) == (_summary(first),)
        with pytest.raises(PersistenceError) as error:
            await _list_summaries(runtime, limit=2)

        assert error.value.context == {
            "operation": "list_field_summaries",
            "reason": "invalid_stored_data",
        }
    finally:
        await runtime.dispose()


async def test_catalogue_leaves_transaction_ownership_with_its_caller(
    migrated_database_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(migrated_database_path)
    definition = _definition()
    try:
        await _store(runtime, definition)

        async with runtime.transaction() as session:
            commit = AsyncMock(side_effect=AssertionError("repository attempted to commit"))
            rollback = AsyncMock(side_effect=AssertionError("repository attempted to roll back"))
            monkeypatch.setattr(session, "commit", commit)
            monkeypatch.setattr(session, "rollback", rollback)

            actual = await SqlAlchemyFieldDefinitionRepository(session).list_summaries(
                limit=20,
                offset=0,
            )

            assert actual == (_summary(definition),)
            assert session.in_transaction() is True
            commit.assert_not_awaited()
            rollback.assert_not_awaited()
    finally:
        await runtime.dispose()


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (SQLAlchemyError("private database statement"), "database_error"),
        (TypeError("private stored value"), "invalid_stored_data"),
        (ValueError("private stored value"), "invalid_stored_data"),
    ],
)
async def test_catalogue_normalizes_driver_and_stored_value_errors(
    failure: Exception,
    reason: str,
) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = failure
    repository = SqlAlchemyFieldDefinitionRepository(session)

    with pytest.raises(PersistenceError, match="could not be completed") as error:
        await repository.list_summaries(limit=20, offset=0)

    assert error.value.context == {"operation": "list_field_summaries", "reason": reason}
    assert "private" not in error.value.public_message
    assert "private" not in repr(error.value.context)
