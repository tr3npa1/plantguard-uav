from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from plantguard_uav.api.routes import fields
from plantguard_uav.config import Environment, Settings, settings_from_values
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.domain import GeoJsonPoint, GeoJsonPolygon, SavedFieldDefinition
from plantguard_uav.domain.field import SavedFieldSummary
from plantguard_uav.errors import PersistenceError
from plantguard_uav.main import create_app
from plantguard_uav.services import GetFieldDefinitionService
from plantguard_uav.services.field_catalogue import ListSavedFieldsService

FIELD_DEFINITION_URL = "/api/v1/fields/definition"
FIELD_CATALOGUE_URL = "/api/v1/fields"
VALID_PARAMETERS = {"field_id": "field-alpha", "sector_id": "sector-north"}
VALIDATION_ERROR = {
    "error": {
        "code": "validation_error",
        "message": "The request contains invalid or missing values.",
    }
}


def _definition() -> SavedFieldDefinition:
    boundary = GeoJsonPolygon(
        coordinates=(((77.0, 28.0), (77.2, 28.0), (77.2, 28.2), (77.0, 28.0)),)
    )
    return SavedFieldDefinition(
        field_id="field-alpha",
        sector_id="sector-north",
        field_name="North Demonstration Field",
        crop_type="wheat",
        field_boundary=boundary,
        sector_boundary=boundary,
        home_location=GeoJsonPoint(coordinates=(77.05, 28.05)),
        exclusion_zones=(),
        field_version="field-version-7",
    )


class LookupStub:
    def __init__(self) -> None:
        self.definition: SavedFieldDefinition | None = _definition()
        self.error: Exception | None = None
        self.exit_error: PersistenceError | None = None
        self.calls: list[tuple[str, str]] = []
        self.events: list[str] = []
        self.runtimes: list[DatabaseRuntime] = []

    async def get_definition(
        self,
        *,
        field_id: str,
        sector_id: str,
    ) -> SavedFieldDefinition | None:
        self.calls.append((field_id, sector_id))
        self.events.append("lookup")
        if self.error is not None:
            raise self.error
        return self.definition

    @asynccontextmanager
    async def service_context(
        self,
        runtime: DatabaseRuntime,
    ) -> AsyncIterator[GetFieldDefinitionService]:
        self.runtimes.append(runtime)
        self.events.append("enter")
        try:
            yield GetFieldDefinitionService(self)
        finally:
            self.events.append("exit")
        if self.exit_error is not None:
            raise self.exit_error


@pytest.fixture
def lookup_stub(monkeypatch: pytest.MonkeyPatch) -> LookupStub:
    stub = LookupStub()
    monkeypatch.setattr(fields, "field_definition_service", stub.service_context)
    return stub


def test_field_lookup_returns_exact_versioned_geojson_and_no_store_header(
    client: TestClient,
    database_runtime: DatabaseRuntime,
    lookup_stub: LookupStub,
) -> None:
    response = client.get(FIELD_DEFINITION_URL, params=VALID_PARAMETERS)

    expected_boundary = {
        "type": "Polygon",
        "coordinates": [[[77.0, 28.0], [77.2, 28.0], [77.2, 28.2], [77.0, 28.0]]],
    }
    assert response.status_code == 200
    assert response.json() == {
        "field_id": "field-alpha",
        "sector_id": "sector-north",
        "field_name": "North Demonstration Field",
        "crop_type": "wheat",
        "field_boundary": expected_boundary,
        "sector_boundary": expected_boundary,
        "home_location": {"type": "Point", "coordinates": [77.05, 28.05]},
        "exclusion_zones": [],
        "field_version": "field-version-7",
        "schema_version": "1.0",
    }
    assert response.headers["cache-control"] == "no-store"
    assert lookup_stub.calls == [("field-alpha", "sector-north")]
    assert lookup_stub.runtimes == [database_runtime]
    assert lookup_stub.events == ["enter", "lookup", "exit"]


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"field_id": "field-alpha"},
        {"sector_id": "sector-north"},
        {"field_id": "", "sector_id": "sector-north"},
        {"field_id": "field-alpha", "sector_id": ""},
        {"field_id": " \t\n ", "sector_id": "sector-north"},
        {"field_id": "field-alpha", "sector_id": " \t\n "},
    ],
)
def test_missing_or_blank_identifiers_fail_before_opening_a_database_context(
    client: TestClient,
    lookup_stub: LookupStub,
    parameters: dict[str, str],
) -> None:
    response = client.get(FIELD_DEFINITION_URL, params=parameters)

    assert response.status_code == 422
    assert response.json() == VALIDATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert lookup_stub.calls == []
    assert lookup_stub.events == []
    assert lookup_stub.runtimes == []


def test_query_identifiers_preserve_opaque_characters_and_trim_surrounding_whitespace(
    client: TestClient,
    lookup_stub: LookupStub,
) -> None:
    field_id = "field/वर्ष?&+%#=1"
    sector_id = "sector/北?&+%#=2"
    definition = _definition().model_copy(update={"field_id": field_id, "sector_id": sector_id})
    lookup_stub.definition = definition

    response = client.get(
        FIELD_DEFINITION_URL,
        params={"field_id": f"  {field_id}\t", "sector_id": f"\t{sector_id}  "},
    )

    assert response.status_code == 200
    assert response.json() == definition.model_dump(mode="json")
    assert lookup_stub.calls == [(field_id, sector_id)]


def test_field_lookup_includes_saved_exclusion_polygons(
    client: TestClient,
    lookup_stub: LookupStub,
) -> None:
    definition = _definition()
    definition = definition.model_copy(update={"exclusion_zones": (definition.field_boundary,)})
    lookup_stub.definition = definition

    response = client.get(FIELD_DEFINITION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 200
    assert response.json() == definition.model_dump(mode="json")
    assert response.json()["exclusion_zones"] == [response.json()["field_boundary"]]


def test_missing_saved_field_returns_safe_not_found_and_closes_context(
    client: TestClient,
    lookup_stub: LookupStub,
) -> None:
    lookup_stub.definition = None

    response = client.get(FIELD_DEFINITION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "The requested saved field sector was not found.",
        }
    }
    assert lookup_stub.events == ["enter", "lookup", "exit"]


def test_persistence_failure_returns_safe_error_and_closes_context(
    client: TestClient,
    lookup_stub: LookupStub,
) -> None:
    lookup_stub.error = PersistenceError(context={"reason": "private-storage-detail"})

    response = client.get(FIELD_DEFINITION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "error": {
            "code": "persistence_error",
            "message": "Persistent storage operation could not be completed.",
        }
    }
    assert "private-storage-detail" not in response.text
    assert lookup_stub.events == ["enter", "lookup", "exit"]


def test_failure_while_finishing_context_prevents_a_success_response(
    client: TestClient,
    lookup_stub: LookupStub,
) -> None:
    lookup_stub.exit_error = PersistenceError(context={"reason": "private-finish-detail"})

    response = client.get(FIELD_DEFINITION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "persistence_error"
    assert "private-finish-detail" not in response.text
    assert "field_boundary" not in response.json()
    assert lookup_stub.events == ["enter", "lookup", "exit"]


def test_unexpected_lookup_failure_returns_traceable_safe_error_and_closes_context(
    app: FastAPI,
    lookup_stub: LookupStub,
) -> None:
    lookup_stub.error = RuntimeError("private-lookup-detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(FIELD_DEFINITION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "internal_server_error"
    assert len(response.json()["error"]["error_id"]) == 32
    assert "private-lookup-detail" not in response.text
    assert lookup_stub.events == ["enter", "lookup", "exit"]


@pytest.mark.parametrize("environment", [Environment.DEVELOPMENT, Environment.TESTING])
def test_field_lookup_is_available_in_development_and_testing(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    lookup_stub: LookupStub,
    environment: Environment,
) -> None:
    settings = settings_from_values(
        {**test_settings.model_dump(), "environment": environment.value}
    )
    app = create_app(settings, database_runtime=database_runtime)

    with TestClient(app) as client:
        response = client.get(FIELD_DEFINITION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 200
    assert lookup_stub.events == ["enter", "lookup", "exit"]


def test_production_does_not_expose_field_lookup_or_open_a_context(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    lookup_stub: LookupStub,
) -> None:
    settings = settings_from_values({**test_settings.model_dump(), "environment": "production"})
    app = create_app(settings, database_runtime=database_runtime)

    with TestClient(app) as client:
        response = client.get(FIELD_DEFINITION_URL, params=VALID_PARAMETERS)

    assert response.status_code == 404
    assert FIELD_DEFINITION_URL not in app.openapi()["paths"]
    assert lookup_stub.calls == []
    assert lookup_stub.events == []


def test_openapi_declares_required_identifiers_and_saved_definition_response(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"][FIELD_DEFINITION_URL]["get"]
    parameters = operation["parameters"]
    assert {parameter["name"] for parameter in parameters} == {"field_id", "sector_id"}
    assert all(parameter["in"] == "query" and parameter["required"] for parameter in parameters)
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SavedFieldDefinition"
    }
    for status_code in ("404", "422", "500"):
        assert operation["responses"][status_code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ApiErrorResponse"
        }


def _summary(*, sector_id: str = "sector-north") -> SavedFieldSummary:
    return SavedFieldSummary(
        field_id="field-alpha",
        sector_id=sector_id,
        field_name="North Demonstration Field",
        crop_type="wheat",
        field_version="field-version-7",
    )


class CatalogueStub:
    def __init__(self) -> None:
        self.summaries: tuple[SavedFieldSummary, ...] = (_summary(),)
        self.error: Exception | None = None
        self.exit_error: PersistenceError | None = None
        self.calls: list[tuple[int, int]] = []
        self.events: list[str] = []
        self.runtimes: list[DatabaseRuntime] = []

    async def list_summaries(self, *, limit: int, offset: int) -> tuple[SavedFieldSummary, ...]:
        self.calls.append((limit, offset))
        self.events.append("list")
        if self.error is not None:
            raise self.error
        return self.summaries

    @asynccontextmanager
    async def service_context(
        self,
        runtime: DatabaseRuntime,
    ) -> AsyncIterator[ListSavedFieldsService]:
        self.runtimes.append(runtime)
        self.events.append("enter")
        try:
            yield ListSavedFieldsService(self)
        finally:
            self.events.append("exit")
        if self.exit_error is not None:
            raise self.exit_error


@pytest.fixture
def catalogue_stub(monkeypatch: pytest.MonkeyPatch) -> CatalogueStub:
    stub = CatalogueStub()
    monkeypatch.setattr(fields, "field_catalogue_service", stub.service_context)
    return stub


def test_catalogue_defaults_return_exact_summary_page_without_geometry(
    client: TestClient,
    database_runtime: DatabaseRuntime,
    catalogue_stub: CatalogueStub,
) -> None:
    response = client.get(FIELD_CATALOGUE_URL)

    assert response.status_code == 200
    assert response.history == []
    assert response.json() == {
        "items": [
            {
                "field_id": "field-alpha",
                "sector_id": "sector-north",
                "field_name": "North Demonstration Field",
                "crop_type": "wheat",
                "field_version": "field-version-7",
                "schema_version": "1.0",
            },
        ],
        "limit": 20,
        "offset": 0,
        "has_more": False,
        "schema_version": "1.0",
    }
    assert response.headers["cache-control"] == "no-store"
    assert catalogue_stub.calls == [(21, 0)]
    assert catalogue_stub.runtimes == [database_runtime]
    assert catalogue_stub.events == ["enter", "list", "exit"]


@pytest.mark.parametrize(("limit", "offset"), [(1, 0), (100, 7), (20, 2**63 - 1)])
def test_catalogue_accepts_pagination_bounds_and_forwards_lookahead(
    client: TestClient,
    catalogue_stub: CatalogueStub,
    limit: int,
    offset: int,
) -> None:
    catalogue_stub.summaries = ()

    response = client.get(FIELD_CATALOGUE_URL, params={"limit": limit, "offset": offset})

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "limit": limit,
        "offset": offset,
        "has_more": False,
        "schema_version": "1.0",
    }
    assert response.headers["cache-control"] == "no-store"
    assert catalogue_stub.calls == [(limit + 1, offset)]


@pytest.mark.parametrize(
    "parameters",
    [
        {"limit": "0"},
        {"limit": "-1"},
        {"limit": "101"},
        {"limit": ""},
        {"limit": "1.5"},
        {"limit": "true"},
        {"limit": "private-invalid-limit"},
        {"limit": "9" * 100},
        {"offset": "-1"},
        {"offset": ""},
        {"offset": "0.5"},
        {"offset": "false"},
        {"offset": "private-invalid-offset"},
        {"offset": str(2**63)},
        {"offset": "9" * 100},
    ],
)
def test_invalid_catalogue_pagination_fails_safely_before_database_access(
    client: TestClient,
    catalogue_stub: CatalogueStub,
    parameters: dict[str, str],
) -> None:
    response = client.get(FIELD_CATALOGUE_URL, params=parameters)

    assert response.status_code == 422
    assert response.json() == VALIDATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert catalogue_stub.calls == []
    assert catalogue_stub.events == []
    assert catalogue_stub.runtimes == []


def test_catalogue_omits_lookahead_item_and_reports_another_page(
    client: TestClient,
    catalogue_stub: CatalogueStub,
) -> None:
    catalogue_stub.summaries = (_summary(), _summary(sector_id="sector-south"))

    response = client.get(FIELD_CATALOGUE_URL, params={"limit": 1, "offset": 4})

    assert response.status_code == 200
    assert response.json() == {
        "items": [_summary().model_dump(mode="json")],
        "limit": 1,
        "offset": 4,
        "has_more": True,
        "schema_version": "1.0",
    }
    assert catalogue_stub.calls == [(2, 4)]


def test_empty_catalogue_returns_a_successful_empty_page(
    client: TestClient,
    catalogue_stub: CatalogueStub,
) -> None:
    catalogue_stub.summaries = ()

    response = client.get(FIELD_CATALOGUE_URL)

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["has_more"] is False
    assert catalogue_stub.events == ["enter", "list", "exit"]


@pytest.mark.parametrize("failure_stage", ["read", "exit"])
def test_catalogue_persistence_failure_closes_context_and_prevents_success(
    client: TestClient,
    catalogue_stub: CatalogueStub,
    failure_stage: str,
) -> None:
    error = PersistenceError(context={"reason": "private-catalogue-failure"})
    if failure_stage == "read":
        catalogue_stub.error = error
    else:
        catalogue_stub.exit_error = error

    response = client.get(FIELD_CATALOGUE_URL)

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "error": {
            "code": "persistence_error",
            "message": "Persistent storage operation could not be completed.",
        },
    }
    assert "private-catalogue-failure" not in response.text
    assert catalogue_stub.events == ["enter", "list", "exit"]


def test_unexpected_catalogue_failure_is_safe_traceable_and_closes_context(
    app: FastAPI,
    catalogue_stub: CatalogueStub,
) -> None:
    catalogue_stub.error = RuntimeError("private-catalogue-failure")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(FIELD_CATALOGUE_URL)

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "internal_server_error"
    assert len(response.json()["error"]["error_id"]) == 32
    assert "private-catalogue-failure" not in response.text
    assert catalogue_stub.events == ["enter", "list", "exit"]


@pytest.mark.parametrize("environment", [Environment.DEVELOPMENT, Environment.TESTING])
def test_catalogue_is_available_in_development_and_testing(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    catalogue_stub: CatalogueStub,
    environment: Environment,
) -> None:
    settings = settings_from_values(
        {**test_settings.model_dump(), "environment": environment.value},
    )
    app = create_app(settings, database_runtime=database_runtime)

    with TestClient(app) as client:
        response = client.get(FIELD_CATALOGUE_URL)

    assert response.status_code == 200
    assert catalogue_stub.events == ["enter", "list", "exit"]


def test_production_does_not_expose_catalogue_or_open_a_context(
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    catalogue_stub: CatalogueStub,
) -> None:
    settings = settings_from_values({**test_settings.model_dump(), "environment": "production"})
    app = create_app(settings, database_runtime=database_runtime)

    with TestClient(app) as client:
        response = client.get(FIELD_CATALOGUE_URL)

    assert response.status_code == 404
    assert FIELD_CATALOGUE_URL not in app.openapi()["paths"]
    assert catalogue_stub.calls == []
    assert catalogue_stub.events == []


def test_openapi_declares_catalogue_pagination_and_page_response(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"][FIELD_CATALOGUE_URL]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert set(parameters) == {"limit", "offset"}
    assert all(
        parameter["in"] == "query" and not parameter["required"]
        for parameter in parameters.values()
    )
    assert parameters["limit"]["schema"]["default"] == 20
    assert parameters["limit"]["schema"]["minimum"] == 1
    assert parameters["limit"]["schema"]["maximum"] == 100
    assert parameters["offset"]["schema"]["default"] == 0
    assert parameters["offset"]["schema"]["minimum"] == 0
    assert parameters["offset"]["schema"]["maximum"] == 2**63 - 1
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SavedFieldPage",
    }
    for status_code in ("422", "500"):
        assert operation["responses"][status_code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ApiErrorResponse",
        }
