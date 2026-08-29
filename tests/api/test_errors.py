from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from plantguard_uav.config import Settings
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.errors import PlantGuardError
from plantguard_uav.main import create_app


class ConflictError(PlantGuardError):
    error_code = "resource_conflict"
    status_code = 409


def _app_with_error_routes(
    settings: Settings,
    database_runtime: DatabaseRuntime,
) -> FastAPI:
    app = create_app(settings, database_runtime=database_runtime)

    @app.get("/known-error")
    def known_error() -> None:
        raise ConflictError(
            "The requested operation conflicts with current state.",
            context={"password": "private-known-secret"},
        )

    @app.get("/unexpected-error")
    def unexpected_error() -> None:
        raise RuntimeError("private implementation detail")

    return app


def test_known_error_returns_declared_safe_response(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app_with_error_routes(test_settings, database_runtime)

    with TestClient(app) as client:
        response = client.get("/known-error")
        rendered_logs = capsys.readouterr().out

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "resource_conflict",
            "message": "The requested operation conflicts with current state.",
        }
    }
    assert "private-known-secret" not in rendered_logs
    assert "[REDACTED]" in rendered_logs


def test_unexpected_error_returns_generic_traceable_response(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
) -> None:
    app = _app_with_error_routes(test_settings, database_runtime)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unexpected-error")

    body = response.json()
    assert response.status_code == 500
    assert body["error"]["code"] == "internal_server_error"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert len(body["error"]["error_id"]) == 32
    assert "private implementation detail" not in response.text
