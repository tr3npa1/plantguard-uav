"""Shared fixtures for the PlantGuard UAV test suite."""

from collections.abc import Iterator
import os
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from plantguard_uav.config import Settings, settings_from_values
from plantguard_uav.db import DatabaseHealth, DatabaseRuntime
from plantguard_uav.main import create_app


@pytest.fixture(autouse=True)
def clear_plantguard_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent a developer's local PlantGuard variables from changing test results."""
    for variable_name in tuple(os.environ):
        if variable_name.upper().startswith("PLANTGUARD_"):
            monkeypatch.delenv(variable_name, raising=False)


@pytest.fixture
def project_root() -> Path:
    """Return the repository root for tests that inspect project files."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def temporary_artifact_dir(tmp_path: Path) -> Path:
    """Provide an isolated artifact directory and leave cleanup to Pytest."""
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    return artifact_dir


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Return validated settings without reading files or the host environment."""
    return settings_from_values(
        {
            "environment": "testing",
            "log_level": "INFO",
            "log_format": "console",
            "api": {"host": "127.0.0.1", "port": 8000},
            "database": {
                "url": f"sqlite+aiosqlite:///{(tmp_path / 'test.sqlite3').as_posix()}",
                "connect_timeout_seconds": 1,
            },
        }
    )


@pytest.fixture
def database_runtime(
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> DatabaseRuntime:
    """Provide a runtime whose readiness result is deterministic for API unit tests."""
    runtime = DatabaseRuntime.from_settings(test_settings.database)
    monkeypatch.setattr(
        runtime,
        "check_health",
        AsyncMock(return_value=DatabaseHealth(connection_ready=True, schema_ready=True)),
    )
    return runtime


@pytest.fixture
def app(test_settings: Settings, database_runtime: DatabaseRuntime) -> FastAPI:
    """Build an isolated API application for a test."""
    return create_app(test_settings, database_runtime=database_runtime)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Run the application lifespan around an HTTP test client."""
    with TestClient(app) as test_client:
        yield test_client
