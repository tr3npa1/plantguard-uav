"""Async SQLAlchemy lifecycle, health checks, and transaction boundary."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import partial
from typing import Protocol, Self, cast

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from plantguard_uav.config import DatabaseSettings
from plantguard_uav.db.schema import SCHEMA_HEAD
from plantguard_uav.errors import PersistenceError

_CONNECTION_PROBE = text("SELECT 1")
_SCHEMA_REVISION_QUERY = text("SELECT version_num FROM alembic_version")


class _Cursor(Protocol):
    """Minimum synchronous cursor behavior needed for SQLite setup."""

    def execute(self, statement: str) -> object:
        """Execute one connection-initialization statement."""
        ...

    def close(self) -> None:
        """Release the temporary cursor."""
        ...


class _DbapiConnection(Protocol):
    """Minimum DBAPI connection behavior needed for SQLite setup."""

    def cursor(self) -> _Cursor:
        """Create a synchronous initialization cursor."""
        ...


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    """Safe readiness result for database connectivity and schema compatibility."""

    connection_ready: bool
    schema_ready: bool

    @property
    def ready(self) -> bool:
        """Return whether both mandatory database checks passed."""
        return self.connection_ready and self.schema_ready


def _configure_sqlite_connection(
    dbapi_connection: object,
    _connection_record: object,
    *,
    busy_timeout_milliseconds: int,
) -> None:
    """Enable SQLite integrity and bounded lock waiting on every connection."""
    connection = cast(_DbapiConnection, dbapi_connection)
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={busy_timeout_milliseconds}")
    finally:
        cursor.close()


class DatabaseRuntime:
    """Own one async engine and create one session per transaction boundary."""

    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        health_timeout_seconds: float,
    ) -> None:
        """Store application-lifetime database resources."""
        self._engine = engine
        self._session_factory = session_factory
        self._health_timeout_seconds = health_timeout_seconds

    @classmethod
    def from_settings(cls, settings: DatabaseSettings) -> Self:
        """Build a runtime without opening a connection until it is first used."""
        try:
            database_url = make_url(settings.url.get_secret_value())
            connect_arguments: dict[str, object] = {}
            if database_url.get_backend_name() == "sqlite":
                connect_arguments["timeout"] = settings.connect_timeout_seconds
            engine = create_async_engine(
                database_url,
                connect_args=connect_arguments,
                pool_pre_ping=True,
            )
        except (ModuleNotFoundError, SQLAlchemyError) as exc:
            raise PersistenceError(
                context={"operation": "initialize"},
            ) from exc

        if engine.url.get_backend_name() == "sqlite":
            busy_timeout_milliseconds = max(
                1,
                round(settings.connect_timeout_seconds * 1000),
            )
            event.listen(
                engine.sync_engine,
                "connect",
                partial(
                    _configure_sqlite_connection,
                    busy_timeout_milliseconds=busy_timeout_milliseconds,
                ),
            )

        session_factory = async_sessionmaker(
            engine,
            autoflush=False,
            autobegin=False,
            expire_on_commit=False,
        )
        return cls(
            engine,
            session_factory,
            health_timeout_seconds=settings.connect_timeout_seconds,
        )

    @property
    def engine(self) -> AsyncEngine:
        """Expose the application engine for lifecycle and migration integration."""
        return self._engine

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """Commit one unit of work, or roll it back when the block raises."""
        try:
            async with self._session_factory.begin() as session:
                yield session
        except SQLAlchemyError as exc:
            raise PersistenceError(
                context={"operation": "transaction"},
            ) from exc

    async def check_health(self) -> DatabaseHealth:
        """Check connectivity and the Alembic revision within one bounded interval."""
        connection_ready = False
        try:
            async with asyncio.timeout(self._health_timeout_seconds):
                async with self._engine.connect() as connection:
                    await connection.execute(_CONNECTION_PROBE)
                    connection_ready = True
                    schema_ready = await self._schema_is_current(connection)
        except TimeoutError:
            return DatabaseHealth(connection_ready=connection_ready, schema_ready=False)
        except (OSError, SQLAlchemyError):
            return DatabaseHealth(connection_ready=False, schema_ready=False)
        return DatabaseHealth(connection_ready=True, schema_ready=schema_ready)

    @staticmethod
    async def _schema_is_current(connection: AsyncConnection) -> bool:
        """Return false for a missing, behind, ahead, or branched revision marker."""
        try:
            result = await connection.execute(_SCHEMA_REVISION_QUERY)
        except (OSError, SQLAlchemyError):
            return False
        return set(result.scalars()) == {SCHEMA_HEAD}

    async def dispose(self) -> None:
        """Release all pooled connections during controlled application shutdown."""
        try:
            await self._engine.dispose()
        except (OSError, SQLAlchemyError) as exc:
            raise PersistenceError(
                context={"operation": "dispose"},
            ) from exc
