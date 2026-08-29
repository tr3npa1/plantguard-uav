"""Smoke tests for the installable PlantGuard UAV package."""

from typing import NoReturn, cast

import aiosqlite
from fastapi import FastAPI
from pydantic import SecretStr
import pytest
import uvicorn

from plantguard_uav import __main__ as command, __version__
from plantguard_uav.config import DatabaseSettings, Settings
from plantguard_uav.db import SCHEMA_HEAD, Base, DatabaseRuntime
from plantguard_uav.errors import ConfigurationError


def test_package_exposes_a_version() -> None:
    """The installed package should expose a non-empty version string."""
    assert __version__


def test_field_selection_contracts_are_publicly_importable() -> None:
    """W1D6 contracts should be reachable through their public package boundaries."""
    from plantguard_uav.domain import (
        GeoJsonLinearRing,
        GeoJsonPoint,
        GeoJsonPolygon,
        SavedFieldDefinition,
        Wgs84Position,
    )
    from plantguard_uav.repositories import (
        FieldDefinitionRepository,
        SqlAlchemyFieldDefinitionRepository,
    )
    from plantguard_uav.services import GetFieldDefinitionQuery, GetFieldDefinitionService

    public_contracts: tuple[object, ...] = (
        Wgs84Position,
        GeoJsonLinearRing,
        GeoJsonPoint,
        GeoJsonPolygon,
        SavedFieldDefinition,
        FieldDefinitionRepository,
        SqlAlchemyFieldDefinitionRepository,
        GetFieldDefinitionQuery,
        GetFieldDefinitionService,
    )

    assert all(contract is not None for contract in public_contracts)


@pytest.mark.asyncio
async def test_persistence_foundation_constructs_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persistence imports and engine construction must not open a database."""

    def reject_connection(*args: object, **kwargs: object) -> NoReturn:
        del args, kwargs
        raise AssertionError("Constructing DatabaseRuntime must not connect.")

    monkeypatch.setattr(aiosqlite, "connect", reject_connection)
    settings = DatabaseSettings(
        url=SecretStr("sqlite+aiosqlite:///:memory:"),
    )
    runtime = DatabaseRuntime.from_settings(settings)

    try:
        assert runtime.engine.url.drivername == "sqlite+aiosqlite"
        assert SCHEMA_HEAD == "0002_saved_field_definitions"
        assert set(Base.metadata.tables) == {"saved_field_definitions"}
    finally:
        await runtime.dispose()


def test_command_line_starts_uvicorn_with_validated_settings(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Settings,
) -> None:
    """The command should pass validated network and logging values to Uvicorn."""
    called_with: dict[str, object] = {}

    def fake_load_settings() -> Settings:
        return test_settings

    def fake_run(
        app: FastAPI,
        *,
        host: str,
        port: int,
        log_level: str,
        log_config: object,
    ) -> None:
        called_with.update(
            {
                "app": app,
                "host": host,
                "port": port,
                "log_level": log_level,
                "log_config": log_config,
            }
        )

    monkeypatch.setattr(command, "load_settings", fake_load_settings)
    monkeypatch.setattr(uvicorn, "run", fake_run)

    assert command.main() == 0
    assert isinstance(called_with["app"], FastAPI)
    assert cast(str, called_with["host"]) == test_settings.api.host
    assert cast(int, called_with["port"]) == test_settings.api.port
    assert called_with["log_level"] == "info"
    assert called_with["log_config"] is None


def test_command_line_reports_configuration_failure_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The command should expose only the safe startup error and return nonzero."""

    def fail_to_load_settings() -> Settings:
        try:
            raise ValueError("private parser detail")
        except ValueError as cause:
            raise ConfigurationError(
                "Application configuration could not be loaded.",
                context={"password": "private-value"},
            ) from cause

    monkeypatch.setattr(command, "load_settings", fail_to_load_settings)

    assert command.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ("configuration_error: Application configuration could not be loaded.\n")
    assert "private" not in captured.err
    assert "Traceback" not in captured.err


def test_command_line_reports_database_startup_failure_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    test_settings: Settings,
) -> None:
    """A database-adapter failure should use the same safe startup boundary."""
    private_url = "missing+async://private-user:private-password@database/plantguard"
    invalid_settings = test_settings.model_copy(
        update={"database": DatabaseSettings(url=SecretStr(private_url))}
    )

    def load_invalid_database_settings() -> Settings:
        return invalid_settings

    monkeypatch.setattr(command, "load_settings", load_invalid_database_settings)

    assert command.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "persistence_error: Persistent storage operation could not be completed.\n"
    )
    assert private_url not in captured.err
    assert "Traceback" not in captured.err
