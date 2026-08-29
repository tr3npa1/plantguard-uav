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
