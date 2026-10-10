"""HTTP configuration examples are synthetic, never approved flight profiles."""

from inspect import iscoroutinefunction
from threading import get_ident
from typing import cast

from fastapi import Request, Response
from fastapi.testclient import TestClient
import pytest
from starlette.middleware.base import RequestResponseEndpoint

from plantguard_uav.api.dependencies import get_inspection_configuration_source
from plantguard_uav.api.routes.inspection_configuration import get_inspection_configuration
from plantguard_uav.config import Environment, Settings, settings_from_values
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration
from plantguard_uav.errors import (
    ConfigurationError,
    InspectionConfigurationError,
    InspectionConfigurationFailureReason,
    InspectionConfigurationUnavailableError,
)
from plantguard_uav.main import create_app

CONFIGURATION_URL = "/api/v1/inspection-configuration"
VALID_PARAMETERS = {
    "configuration_id": "synthetic-api-configuration",
    "configuration_version": "synthetic-revision-a",
}
VALIDATION_ERROR = {
    "error": {
        "code": "validation_error",
        "message": "The request contains invalid or missing values.",
    }
}
CONFIGURATION_ERROR = {
    "error": {
        "code": "configuration_error",
        "message": "Inspection configuration could not be loaded.",
    }
}


class ConfigurationSourceStub:
    def __init__(self, configuration: InspectionFlightConfiguration) -> None:
        self.configuration: object = configuration
        self.error: Exception | None = None
        self.calls = 0
        self.thread_ids: list[int] = []

    def load(self) -> InspectionFlightConfiguration:
        self.calls += 1
        self.thread_ids.append(get_ident())
        if self.error is not None:
            raise self.error
        return cast(InspectionFlightConfiguration, self.configuration)


@pytest.fixture
def synthetic_configuration() -> InspectionFlightConfiguration:
    return InspectionFlightConfiguration.model_validate(
        {
            **VALID_PARAMETERS,
            "operating_environment": "nominal_dry_daylight",
            "survey": {
                "altitude_agl_m": 12,
                "speed_m_s": 3,
                "front_overlap_fraction": 0.5,
                "side_overlap_fraction": 0.25,
            },
            "revisit": {"altitude_agl_m": 6, "speed_m_s": 4},
        }
    )


@pytest.fixture
def source(synthetic_configuration: InspectionFlightConfiguration) -> ConfigurationSourceStub:
    return ConfigurationSourceStub(synthetic_configuration)


@pytest.mark.parametrize("environment", [Environment.DEVELOPMENT, Environment.TESTING])
def test_configuration_endpoint_returns_complete_versioned_model_without_caching(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    synthetic_configuration: InspectionFlightConfiguration,
    environment: Environment,
) -> None:
    settings = settings_from_values({**test_settings.model_dump(), "environment": environment})
    app = create_app(
        settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app) as client:
        response = client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        **VALID_PARAMETERS,
        "operating_environment": "nominal_dry_daylight",
        "survey": {
            "altitude_agl_m": 12.0,
            "speed_m_s": 3.0,
            "front_overlap_fraction": 0.5,
            "side_overlap_fraction": 0.25,
            "schema_version": "1.0",
        },
        "revisit": {"altitude_agl_m": 6.0, "speed_m_s": 4.0, "schema_version": "1.0"},
        "schema_version": "1.0",
    }
    assert source.configuration is synthetic_configuration
    assert source.calls == 1


def test_configuration_query_trims_only_surrounding_whitespace_and_preserves_opaque_identity(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    identity = "Synthetic/वर्ष?&+%#=🌾"
    revision = "REV / 北?&+%#=2"
    configuration = synthetic_configuration.model_copy(
        update={"configuration_id": identity, "configuration_version": revision}
    )
    source.configuration = configuration
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app) as client:
        response = client.get(
            CONFIGURATION_URL,
            params={
                "configuration_id": f" \t{identity} ",
                "configuration_version": f" {revision}\t",
            },
        )

    assert response.status_code == 200
    assert response.json() == configuration.model_dump(mode="json")
    assert source.calls == 1


@pytest.mark.parametrize("configured", [False, True])
@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"configuration_id": VALID_PARAMETERS["configuration_id"]},
        {"configuration_version": VALID_PARAMETERS["configuration_version"]},
        {**VALID_PARAMETERS, "configuration_id": ""},
        {**VALID_PARAMETERS, "configuration_version": ""},
        {**VALID_PARAMETERS, "configuration_id": " \t\n "},
        {**VALID_PARAMETERS, "configuration_version": " \t\n "},
    ],
)
def test_invalid_query_returns_safe_validation_error_before_source_load_or_unavailability(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    parameters: dict[str, str],
    configured: bool,
) -> None:
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source if configured else None,
    )

    with TestClient(app) as client:
        response = client.get(CONFIGURATION_URL, params=parameters)

    assert response.status_code == 422
    assert response.json() == VALIDATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert source.calls == 0


def test_unconfigured_source_returns_safe_service_unavailable(client: TestClient) -> None:
    response = client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "error": {
            "code": "configuration_error",
            "message": "Inspection configuration source is not configured.",
        }
    }


def test_unavailable_error_has_fixed_message_and_controlled_context() -> None:
    error = InspectionConfigurationUnavailableError()

    assert isinstance(error, ConfigurationError)
    assert error.status_code == 503
    assert error.error_code == "configuration_error"
    assert (
        str(error) == error.public_message == "Inspection configuration source is not configured."
    )
    assert error.context == {
        "operation": "load_inspection_configuration",
        "reason": "source_not_configured",
    }


@pytest.mark.parametrize(
    "reason",
    [
        "invalid_input",
        "file_unavailable",
        "not_regular_file",
        "input_too_large",
        "invalid_encoding",
        "invalid_json",
        "duplicate_key",
        "nonfinite_number",
        "invalid_configuration",
        "identity_mismatch",
    ],
)
def test_controlled_source_errors_do_not_expose_paths_or_input_in_response_or_logs(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    capsys: pytest.CaptureFixture[str],
    reason: InspectionConfigurationFailureReason,
) -> None:
    private_path = "private-source-folder/private-profile.json"
    private_input = "private-invalid-configuration-input"
    error = InspectionConfigurationError(reason=reason)
    error.__context__ = ValueError(f"{private_path}: {private_input}")
    source.error = error
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app) as client:
        response = client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)
        rendered_logs = capsys.readouterr().out

    assert response.status_code == 500
    assert response.json() == CONFIGURATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert private_path not in response.text + rendered_logs
    assert private_input not in response.text + rendered_logs
    assert source.calls == 1


@pytest.mark.parametrize("field", ["configuration_id", "configuration_version"])
def test_identity_mismatch_returns_safe_configuration_error(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    capsys: pytest.CaptureFixture[str],
    field: str,
) -> None:
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app) as client:
        response = client.get(
            CONFIGURATION_URL, params={**VALID_PARAMETERS, field: "private-mismatched-identity"}
        )
        rendered_logs = capsys.readouterr().out

    assert response.status_code == 500
    assert response.json() == CONFIGURATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert "identity_mismatch" in rendered_logs
    application_error_logs = "\n".join(
        line for line in rendered_logs.splitlines() if "request_failed" in line
    )
    assert "private-mismatched-identity" not in response.text + application_error_logs
    assert source.calls == 1


@pytest.mark.parametrize("invalid_result", [None, {}, "private-invalid-source-result"])
def test_invalid_source_result_is_revalidated_and_rejected(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    invalid_result: object,
) -> None:
    source.configuration = invalid_result
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app) as client:
        response = client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 500
    assert response.json() == CONFIGURATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert source.calls == 1


def test_unchecked_configuration_model_does_not_bypass_validation(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    values = synthetic_configuration.model_dump()
    values["operating_environment"] = "private-unapproved-environment"
    source.configuration = InspectionFlightConfiguration.model_construct(**values)
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app) as client:
        response = client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 500
    assert response.json() == CONFIGURATION_ERROR
    assert "private-unapproved-environment" not in response.text


def test_unexpected_source_error_has_generic_traceable_public_response(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
) -> None:
    source.error = RuntimeError("private unexpected source implementation detail")
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)

    error = response.json()["error"]
    assert response.status_code == 500
    assert error["code"] == "internal_server_error"
    assert error["message"] == "An unexpected error occurred."
    assert len(error["error_id"]) == 32
    assert response.headers["cache-control"] == "no-store"
    assert "private unexpected source implementation detail" not in response.text
    assert source.calls == 1


def test_configuration_source_is_not_loaded_during_construction_startup_or_health_request(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
) -> None:
    source.error = RuntimeError("source must not be called eagerly")
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )
    assert source.calls == 0

    with TestClient(app) as client:
        assert source.calls == 0
        assert client.get("/health/live").status_code == 200
        assert source.calls == 0

    assert source.calls == 0


@pytest.mark.parametrize("configured", [False, True])
def test_production_excludes_endpoint_and_its_openapi_schema_even_with_a_source(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    configured: bool,
) -> None:
    settings = settings_from_values({**test_settings.model_dump(), "environment": "production"})
    app = create_app(
        settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source if configured else None,
    )

    with TestClient(app) as client:
        response = client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)
        assert client.get("/openapi.json").status_code == 404

    assert response.status_code == 404
    assert CONFIGURATION_URL not in app.openapi()["paths"]
    assert "InspectionFlightConfiguration" not in app.openapi().get("components", {}).get(
        "schemas", {}
    )
    assert source.calls == 0


def test_openapi_describes_query_response_and_safe_failure_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"][CONFIGURATION_URL]["get"]

    assert set(operation["responses"]) == {"200", "422", "500", "503"}
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert set(parameters) == set(VALID_PARAMETERS)
    for parameter in parameters.values():
        assert parameter["in"] == "query"
        assert parameter["required"] is True
        assert parameter["schema"]["$ref"] == "#/components/schemas/OpaqueIdentifier"
    identifier_schema = schema["components"]["schemas"]["OpaqueIdentifier"]
    assert identifier_schema["type"] == "string"
    assert identifier_schema["minLength"] == 1
    success_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert success_schema == {"$ref": "#/components/schemas/InspectionFlightConfiguration"}
    for status in ("422", "500", "503"):
        error_schema = operation["responses"][status]["content"]["application/json"]["schema"]
        assert error_schema == {"$ref": "#/components/schemas/ApiErrorResponse"}


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_configuration_endpoint_has_no_mutating_http_methods(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    method: str,
) -> None:
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app) as client:
        response = client.request(method, CONFIGURATION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 405
    assert source.calls == 0


def test_configuration_source_runs_in_worker_thread_not_request_event_loop(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
) -> None:
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )
    event_loop_threads: list[int] = []

    @app.middleware("http")
    async def record_event_loop_thread(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        event_loop_threads.append(get_ident())
        return await call_next(request)

    with TestClient(app) as client:
        response = client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 200
    assert len(event_loop_threads) == len(source.thread_ids) == 1
    assert source.thread_ids[0] != event_loop_threads[0]
    assert not iscoroutinefunction(get_inspection_configuration)


def test_extra_query_parameters_do_not_choose_a_different_configuration_source(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )

    with TestClient(app) as client:
        response = client.get(
            CONFIGURATION_URL,
            params={**VALID_PARAMETERS, "file_path": "../../private-profile.json"},
        )

    assert response.status_code == 200
    assert response.json() == synthetic_configuration.model_dump(mode="json")
    assert source.calls == 1


def test_source_dependency_returns_optional_app_local_source_without_loading(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
) -> None:
    configured_app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )
    unconfigured_app = create_app(test_settings, database_runtime=database_runtime)

    assert (
        get_inspection_configuration_source(Request({"type": "http", "app": configured_app}))
        is source
    )
    assert (
        get_inspection_configuration_source(Request({"type": "http", "app": unconfigured_app}))
        is None
    )
    assert source.calls == 0


def test_separate_apps_keep_their_configuration_sources_isolated(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    source: ConfigurationSourceStub,
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    other_configuration = synthetic_configuration.model_copy(
        update={"configuration_version": "synthetic-revision-b"}
    )
    other_source = ConfigurationSourceStub(other_configuration)
    first_app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )
    second_app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=other_source,
    )

    with TestClient(first_app) as first_client, TestClient(second_app) as second_client:
        first_response = first_client.get(CONFIGURATION_URL, params=VALID_PARAMETERS)
        second_response = second_client.get(
            CONFIGURATION_URL,
            params={**VALID_PARAMETERS, "configuration_version": "synthetic-revision-b"},
        )

    assert first_response.status_code == second_response.status_code == 200
    assert first_response.json() == synthetic_configuration.model_dump(mode="json")
    assert second_response.json() == other_configuration.model_dump(mode="json")
    assert source.calls == other_source.calls == 1
