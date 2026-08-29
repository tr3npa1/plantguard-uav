from inspect import Parameter, signature

from pydantic import ValidationError
import pytest

from plantguard_uav.domain import GeoJsonPoint, GeoJsonPolygon, SavedFieldDefinition
from plantguard_uav.domain.value_objects import OpaqueIdentifier
from plantguard_uav.errors import FieldNotFoundError, PersistenceError
from plantguard_uav.repositories import FieldDefinitionRepository
from plantguard_uav.services import GetFieldDefinitionQuery, GetFieldDefinitionService

FIELD_RING = (
    (77.20, 28.61),
    (77.23, 28.61),
    (77.23, 28.64),
    (77.20, 28.61),
)
SECTOR_RING = (
    (77.205, 28.615),
    (77.22, 28.615),
    (77.22, 28.63),
    (77.205, 28.615),
)


class FakeFieldDefinitionRepository:
    def __init__(self, results: list[SavedFieldDefinition | None]) -> None:
        self._results = results.copy()
        self.calls: list[tuple[OpaqueIdentifier, OpaqueIdentifier]] = []

    async def get_definition(
        self,
        *,
        field_id: OpaqueIdentifier,
        sector_id: OpaqueIdentifier,
    ) -> SavedFieldDefinition | None:
        self.calls.append((field_id, sector_id))
        return self._results.pop(0)


class FailingFieldDefinitionRepository:
    def __init__(self, error: PersistenceError) -> None:
        self._error = error

    async def get_definition(
        self,
        *,
        field_id: OpaqueIdentifier,
        sector_id: OpaqueIdentifier,
    ) -> SavedFieldDefinition | None:
        del field_id, sector_id
        raise self._error


def _polygon(ring: tuple[tuple[float, float], ...]) -> GeoJsonPolygon:
    return GeoJsonPolygon(coordinates=(ring,))


def _definition(
    *,
    field_id: str = "field_01",
    sector_id: str = "sector_01",
    field_version: str = "field-version-01",
) -> SavedFieldDefinition:
    return SavedFieldDefinition(
        field_id=field_id,
        sector_id=sector_id,
        field_name="North Field",
        crop_type="Wheat",
        field_boundary=_polygon(FIELD_RING),
        sector_boundary=_polygon(SECTOR_RING),
        home_location=GeoJsonPoint(coordinates=(77.204, 28.614)),
        field_version=field_version,
    )


def _set_attribute(instance: object, attribute: str, value: object) -> None:
    setattr(instance, attribute, value)


def test_query_is_strict_frozen_normalized_and_versioned() -> None:
    query = GetFieldDefinitionQuery(
        field_id="  field_01  ",
        sector_id="  sector_01  ",
    )

    assert query.model_dump(mode="json") == {
        "field_id": "field_01",
        "sector_id": "sector_01",
        "schema_version": "1.0",
    }
    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(query, "field_id", "field_02")


@pytest.mark.parametrize(
    "values",
    [
        {"field_id": "", "sector_id": "sector_01"},
        {"field_id": "field_01", "sector_id": "   "},
        {"field_id": b"field_01", "sector_id": "sector_01"},
        {"field_id": "field_01", "sector_id": b"sector_01"},
        {"field_id": "field_01", "sector_id": "sector_01", "schema_version": "2.0"},
        {"field_id": "field_01", "sector_id": "sector_01", "unexpected": True},
    ],
)
def test_query_rejects_invalid_identifiers_versions_and_extra_fields(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        GetFieldDefinitionQuery.model_validate(values)


def test_repository_protocol_requires_exact_keyword_only_identifiers() -> None:
    method_parameters = signature(FieldDefinitionRepository.get_definition).parameters

    assert tuple(method_parameters) == ("self", "field_id", "sector_id")
    assert method_parameters["field_id"].kind is Parameter.KEYWORD_ONLY
    assert method_parameters["sector_id"].kind is Parameter.KEYWORD_ONLY


async def test_service_returns_the_repository_object_without_mutating_it() -> None:
    definition = _definition()
    original_values = definition.model_dump(round_trip=True)
    fake = FakeFieldDefinitionRepository([definition])
    repository: FieldDefinitionRepository = fake
    service = GetFieldDefinitionService(repository)

    result = await service.execute(
        GetFieldDefinitionQuery(field_id="field_01", sector_id="sector_01")
    )

    assert result is definition
    assert result.model_dump(round_trip=True) == original_values
    assert fake.calls == [("field_01", "sector_01")]


async def test_missing_definition_becomes_one_fixed_safe_not_found_error() -> None:
    fake = FakeFieldDefinitionRepository([None])
    service = GetFieldDefinitionService(fake)

    with pytest.raises(FieldNotFoundError) as caught:
        await service.execute(
            GetFieldDefinitionQuery(field_id="private-field", sector_id="private-sector")
        )

    error = caught.value
    assert error.error_code == "not_found"
    assert error.status_code == 404
    assert error.public_message == "The requested saved field sector was not found."
    assert "private-field" not in error.public_message
    assert "private-sector" not in error.public_message
    assert error.context == {
        "field_id": "private-field",
        "sector_id": "private-sector",
    }
    assert fake.calls == [("private-field", "private-sector")]


@pytest.mark.parametrize(
    "definition",
    [
        _definition(field_id="different-field"),
        _definition(sector_id="different-sector"),
    ],
)
async def test_mismatched_repository_identity_becomes_a_safe_persistence_error(
    definition: SavedFieldDefinition,
) -> None:
    fake = FakeFieldDefinitionRepository([definition])
    service = GetFieldDefinitionService(fake)

    with pytest.raises(PersistenceError) as caught:
        await service.execute(GetFieldDefinitionQuery(field_id="field_01", sector_id="sector_01"))

    assert caught.value.error_code == "persistence_error"
    assert caught.value.public_message == "Persistent storage operation could not be completed."
    assert caught.value.context == {
        "operation": "get_field_definition",
        "reason": "identity_mismatch",
    }
    assert "different" not in caught.value.public_message
    assert fake.calls == [("field_01", "sector_01")]


async def test_repository_persistence_error_propagates_unchanged() -> None:
    original_error = PersistenceError(context={"operation": "field_lookup"})
    service = GetFieldDefinitionService(FailingFieldDefinitionRepository(original_error))

    with pytest.raises(PersistenceError) as caught:
        await service.execute(GetFieldDefinitionQuery(field_id="field_01", sector_id="sector_01"))

    assert caught.value is original_error


async def test_repeated_queries_perform_fresh_authoritative_repository_reads() -> None:
    first_definition = _definition(field_version="field-version-01")
    changed_definition = _definition(field_version="field-version-02")
    fake = FakeFieldDefinitionRepository([first_definition, changed_definition])
    service = GetFieldDefinitionService(fake)
    query = GetFieldDefinitionQuery(field_id="field_01", sector_id="sector_01")

    first_result = await service.execute(query)
    second_result = await service.execute(query)

    assert first_result is first_definition
    assert second_result is changed_definition
    assert second_result.field_version == "field-version-02"
    assert fake.calls == [
        ("field_01", "sector_01"),
        ("field_01", "sector_01"),
    ]
