from pathlib import Path

from pydantic import SecretStr
import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from plantguard_uav.config import DatabaseSettings
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.errors import PersistenceError

_METADATA = MetaData()
_ENTRIES = Table(
    "transaction_test_entries",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("value", String(50), nullable=False),
)


def _settings(path: Path) -> DatabaseSettings:
    return DatabaseSettings(
        url=SecretStr(f"sqlite+aiosqlite:///{path.as_posix()}"),
        connect_timeout_seconds=1.0,
    )


async def _runtime_with_table(path: Path) -> DatabaseRuntime:
    runtime = DatabaseRuntime.from_settings(_settings(path))
    async with runtime.engine.begin() as connection:
        await connection.run_sync(_METADATA.create_all)
    return runtime


async def _entry_count(runtime: DatabaseRuntime) -> int:
    async with runtime.transaction() as session:
        count = await session.scalar(select(func.count()).select_from(_ENTRIES))
    assert count is not None
    return count


async def _insert_then_raise_application_error(runtime: DatabaseRuntime) -> None:
    async with runtime.transaction() as session:
        await session.execute(insert(_ENTRIES).values(id=1, value="rolled-back"))
        raise RuntimeError("application failure")


async def _insert_duplicate_keys(runtime: DatabaseRuntime) -> None:
    async with runtime.transaction() as session:
        await session.execute(insert(_ENTRIES).values(id=1, value="first"))
        await session.execute(insert(_ENTRIES).values(id=1, value="private-value"))


async def test_transaction_commits_on_normal_exit(tmp_path: Path) -> None:
    runtime = await _runtime_with_table(tmp_path / "commit.sqlite3")
    try:
        async with runtime.transaction() as session:
            assert session.in_transaction() is True
            await session.execute(insert(_ENTRIES).values(id=1, value="committed"))

        assert await _entry_count(runtime) == 1
    finally:
        await runtime.dispose()


async def test_transaction_rolls_back_and_preserves_application_exception(tmp_path: Path) -> None:
    runtime = await _runtime_with_table(tmp_path / "rollback.sqlite3")
    try:
        with pytest.raises(RuntimeError, match="application failure"):
            await _insert_then_raise_application_error(runtime)

        assert await _entry_count(runtime) == 0
    finally:
        await runtime.dispose()


async def test_transaction_normalizes_database_errors_without_private_details(
    tmp_path: Path,
) -> None:
    runtime = await _runtime_with_table(tmp_path / "failure.sqlite3")
    try:
        with pytest.raises(PersistenceError, match="could not be completed") as error:
            await _insert_duplicate_keys(runtime)

        assert error.value.context == {"operation": "transaction"}
        assert "private-value" not in error.value.public_message
        assert await _entry_count(runtime) == 0
    finally:
        await runtime.dispose()


async def test_each_transaction_receives_a_fresh_session(tmp_path: Path) -> None:
    runtime = await _runtime_with_table(tmp_path / "sessions.sqlite3")
    sessions: list[AsyncSession] = []
    try:
        async with runtime.transaction() as first_session:
            sessions.append(first_session)
        async with runtime.transaction() as second_session:
            sessions.append(second_session)
    finally:
        await runtime.dispose()

    assert sessions[0] is not sessions[1]
