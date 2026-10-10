from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
import pytest

from plantguard_uav.config import Settings
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.errors import PlantGuardError
from plantguard_uav.main import create_app


class ConflictError(PlantGuardError):
    error_code = "resource_conflict"
    status_code = 409


class ValidationPayload(BaseModel):
    count: int = Field(ge=1)


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

    @app.post("/validate-body")
    def validate_body(payload: ValidationPayload) -> ValidationPayload:
        return payload

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


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"count": "private-submitted-secret"},
        {"count": 0, "password": "private-submitted-secret"},
    ],
)
def test_request_validation_uses_safe_envelope_without_input_leaks(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    capsys: pytest.CaptureFixture[str],
    payload: dict[str, object],
) -> None:
    app = _app_with_error_routes(test_settings, database_runtime)

    with TestClient(app) as client:
        response = client.post("/validate-body", json=payload)
        rendered_logs = capsys.readouterr().out

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "The request contains invalid or missing values.",
        }
    }
    assert response.headers["cache-control"] == "no-store"
    assert "private-submitted-secret" not in response.text
    assert "private-submitted-secret" not in rendered_logs
    assert "request_validation_failed" in rendered_logs


def test_malformed_json_is_a_safe_validation_error(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _app_with_error_routes(test_settings, database_runtime)

    with TestClient(app) as client:
        response = client.post(
            "/validate-body",
            content='{"count": "private-malformed-secret"',
            headers={"Content-Type": "application/json"},
        )
        rendered_logs = capsys.readouterr().out

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "private-malformed-secret" not in response.text
    assert "private-malformed-secret" not in rendered_logs
