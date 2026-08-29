import asyncio
from pathlib import Path
from types import TracebackType
from typing import cast
from unittest.mock import MagicMock

from pydantic import SecretStr
import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, async_sessionmaker

from plantguard_uav.config import DatabaseSettings
from plantguard_uav.db import SCHEMA_HEAD, Base, DatabaseHealth, DatabaseRuntime
import plantguard_uav.db.runtime as runtime_module
from plantguard_uav.errors import PersistenceError


def _settings(path: Path, *, timeout: float = 0.25) -> DatabaseSettings:
    return DatabaseSettings(
        url=SecretStr(f"sqlite+aiosqlite:///{path.as_posix()}"),
        connect_timeout_seconds=timeout,
    )


async def _set_schema_revision(runtime: DatabaseRuntime, revision: str) -> None:
    async with runtime.engine.begin() as connection:
        await connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY NOT NULL)")
        )
        await connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": revision},
        )


def test_declarative_base_has_stable_migration_naming_conventions() -> None:
    assert Base.metadata.naming_convention == {
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(column_0_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
    assert set(Base.metadata.tables) == {"saved_field_definitions"}


def test_sqlite_connection_initialization_always_closes_its_cursor() -> None:
    cursor = MagicMock()
    connection = MagicMock()
    connection.cursor.return_value = cursor

    runtime_module._configure_sqlite_connection(
        connection,
        object(),
        busy_timeout_milliseconds=250,
    )

    assert [invocation.args[0] for invocation in cursor.execute.call_args_list] == [
        "PRAGMA foreign_keys=ON",
        "PRAGMA busy_timeout=250",
    ]
    cursor.close.assert_called_once_with()


def test_non_sqlite_runtime_preserves_generic_engine_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = MagicMock(spec=AsyncEngine)
    engine.url = make_url("postgresql+asyncpg://database/plantguard")
    captured_arguments: dict[str, object] = {}

    def fake_create_async_engine(database_url: URL, **kwargs: object) -> AsyncEngine:
        captured_arguments["database_url"] = database_url
        captured_arguments.update(kwargs)
        return cast(AsyncEngine, engine)

    monkeypatch.setattr(runtime_module, "create_async_engine", fake_create_async_engine)

    runtime = DatabaseRuntime.from_settings(
        DatabaseSettings(
            url=SecretStr("postgresql+asyncpg://database/plantguard"),
            connect_timeout_seconds=1.0,
        )
    )

    assert runtime.engine is engine
    assert captured_arguments["connect_args"] == {}
    assert captured_arguments["pool_pre_ping"] is True


async def test_health_distinguishes_connection_from_missing_schema(tmp_path: Path) -> None:
    runtime = DatabaseRuntime.from_settings(_settings(tmp_path / "health.sqlite3"))
    try:
        health = await runtime.check_health()
    finally:
        await runtime.dispose()

    assert health == DatabaseHealth(connection_ready=True, schema_ready=False)
    assert health.ready is False


async def test_health_accepts_only_the_expected_schema_head(tmp_path: Path) -> None:
    runtime = DatabaseRuntime.from_settings(_settings(tmp_path / "current.sqlite3"))
    try:
        await _set_schema_revision(runtime, SCHEMA_HEAD)

        health = await runtime.check_health()
    finally:
        await runtime.dispose()

    assert health == DatabaseHealth(connection_ready=True, schema_ready=True)
    assert health.ready is True


@pytest.mark.parametrize("revision", ["older_revision", "future_revision"])
async def test_health_rejects_a_different_schema_head(tmp_path: Path, revision: str) -> None:
    runtime = DatabaseRuntime.from_settings(_settings(tmp_path / f"{revision}.sqlite3"))
    try:
        await _set_schema_revision(runtime, revision)

        health = await runtime.check_health()
    finally:
        await runtime.dispose()

    assert health == DatabaseHealth(connection_ready=True, schema_ready=False)


async def test_health_reports_an_unreachable_database(tmp_path: Path) -> None:
    runtime = DatabaseRuntime.from_settings(_settings(tmp_path / "missing" / "database.sqlite3"))
    try:
        health = await runtime.check_health()
    finally:
        await runtime.dispose()

    assert health == DatabaseHealth(connection_ready=False, schema_ready=False)


async def test_sqlite_connections_enable_integrity_and_busy_timeout(tmp_path: Path) -> None:
    runtime = DatabaseRuntime.from_settings(_settings(tmp_path / "pragmas.sqlite3", timeout=0.321))
    try:
        async with runtime.engine.connect() as connection:
            foreign_keys = await connection.scalar(text("PRAGMA foreign_keys"))
            busy_timeout = await connection.scalar(text("PRAGMA busy_timeout"))
    finally:
        await runtime.dispose()

    assert foreign_keys == 1
    assert busy_timeout == 321


class _SlowConnectionContext:
    async def __aenter__(self) -> AsyncConnection:
        await asyncio.sleep(60)
        raise AssertionError("the health timeout should cancel this connection attempt")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return None


async def test_health_timeout_fails_closed() -> None:
    engine = MagicMock(spec=AsyncEngine)
    engine.connect.return_value = _SlowConnectionContext()
    runtime = DatabaseRuntime(
        cast(AsyncEngine, engine),
        async_sessionmaker(),
        health_timeout_seconds=0.001,
    )

    assert await runtime.check_health() == DatabaseHealth(
        connection_ready=False,
        schema_ready=False,
    )


def test_invalid_driver_is_normalized_without_exposing_the_url() -> None:
    private_url = "missing+private://operator:secret-password@database/plantguard"

    with pytest.raises(PersistenceError, match="could not be completed") as error:
        DatabaseRuntime.from_settings(
            DatabaseSettings(
                url=SecretStr(private_url),
                connect_timeout_seconds=1.0,
            )
        )

    assert error.value.context == {"operation": "initialize"}
    assert private_url not in error.value.public_message
    assert "secret-password" not in error.value.public_message


async def test_dispose_normalizes_driver_failures() -> None:
    engine = MagicMock(spec=AsyncEngine)
    engine.dispose.side_effect = OSError("private driver detail")
    runtime = DatabaseRuntime(
        cast(AsyncEngine, engine),
        async_sessionmaker(),
        health_timeout_seconds=1.0,
    )

    with pytest.raises(PersistenceError, match="could not be completed") as error:
        await runtime.dispose()

    assert error.value.context == {"operation": "dispose"}
    assert "private driver detail" not in error.value.public_message
