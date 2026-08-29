from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from plantguard_uav import __version__
from plantguard_uav.config import settings_from_values
from plantguard_uav.db import DatabaseHealth, DatabaseRuntime
from plantguard_uav.main import create_app


def _is_ready(app: FastAPI) -> bool:
    return bool(app.state.ready)


def test_liveness_reports_service_and_version(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "plantguard-uav",
        "version": __version__,
    }


def test_readiness_reports_ready_after_startup(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "api_process": "ready",
            "database_connection": "ready",
            "database_schema": "ready",
        },
    }


def test_readiness_returns_503_when_process_is_not_ready(
    app: FastAPI,
    client: TestClient,
) -> None:
    app.state.ready = False

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "api_process": "not_ready",
            "database_connection": "ready",
            "database_schema": "ready",
        },
    }


@pytest.mark.parametrize(
    ("database_health", "expected_checks"),
    [
        (
            DatabaseHealth(connection_ready=False, schema_ready=False),
            {"database_connection": "not_ready", "database_schema": "not_ready"},
        ),
        (
            DatabaseHealth(connection_ready=True, schema_ready=False),
            {"database_connection": "ready", "database_schema": "not_ready"},
        ),
    ],
)
def test_readiness_fails_when_database_is_unavailable_or_unmigrated(
    app: FastAPI,
    database_runtime: DatabaseRuntime,
    monkeypatch: pytest.MonkeyPatch,
    database_health: DatabaseHealth,
    expected_checks: dict[str, str],
) -> None:
    async def check_database_health() -> DatabaseHealth:
        return database_health

    monkeypatch.setattr(database_runtime, "check_health", check_database_health)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"api_process": "ready", **expected_checks},
    }


def test_liveness_does_not_query_the_database(
    app: FastAPI,
    database_runtime: DatabaseRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_called() -> DatabaseHealth:
        raise AssertionError("liveness must not depend on persistence")

    monkeypatch.setattr(database_runtime, "check_health", fail_if_called)

    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200


def test_lifespan_sets_and_clears_readiness_and_disposes_database(
    app: FastAPI,
    database_runtime: DatabaseRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispose = AsyncMock(wraps=database_runtime.dispose)
    monkeypatch.setattr(database_runtime, "dispose", dispose)
    assert _is_ready(app) is False

    with TestClient(app):
        assert _is_ready(app) is True
        dispose.assert_not_awaited()

    assert _is_ready(app) is False
    dispose.assert_awaited_once_with()


def test_development_exposes_interactive_documentation(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_production_disables_documentation_and_schema(
    database_runtime: DatabaseRuntime,
) -> None:
    settings = settings_from_values(
        {
            "environment": "production",
            "log_level": "INFO",
            "log_format": "json",
            "api": {"host": "0.0.0.0", "port": 8000},
        }
    )
    app = create_app(settings, database_runtime=database_runtime)

    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
