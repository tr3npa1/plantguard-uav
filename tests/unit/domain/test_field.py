from pydantic import ValidationError
import pytest

from plantguard_uav.domain import GeoJsonPoint, GeoJsonPolygon, SavedFieldDefinition

FIELD_RING = [
    [77.20, 28.61],
    [77.23, 28.61],
    [77.23, 28.64],
    [77.20, 28.61],
]
SECTOR_RING = [
    [77.205, 28.615],
    [77.22, 28.615],
    [77.22, 28.63],
    [77.205, 28.615],
]
EXCLUSION_RING = [
    [77.210, 28.620],
    [77.212, 28.620],
    [77.212, 28.622],
    [77.210, 28.620],
]


def _polygon(ring: list[list[float]]) -> GeoJsonPolygon:
    return GeoJsonPolygon.model_validate({"coordinates": [ring]})


def _valid_field_values() -> dict[str, object]:
    return {
        "field_id": "field_01",
        "sector_id": "sector_01",
        "field_name": "North Field",
        "crop_type": "Wheat",
        "field_boundary": _polygon(FIELD_RING),
        "sector_boundary": _polygon(SECTOR_RING),
        "home_location": GeoJsonPoint.model_validate({"coordinates": [77.204, 28.614]}),
        "exclusion_zones": [_polygon(EXCLUSION_RING)],
        "field_version": "field-version-01",
    }


def _set_attribute(instance: object, attribute: str, value: object) -> None:
    setattr(instance, attribute, value)


def test_saved_field_definition_retains_selected_sector_and_exact_geojson() -> None:
    definition = SavedFieldDefinition.model_validate(_valid_field_values())

    assert definition.field_id == "field_01"
    assert definition.sector_id == "sector_01"
    assert definition.field_version == "field-version-01"
    assert definition.schema_version == "1.0"
    assert isinstance(definition.exclusion_zones, tuple)
    serialized = definition.model_dump(mode="json")
    assert serialized["field_boundary"] == {
        "type": "Polygon",
        "coordinates": [FIELD_RING],
    }
    assert serialized["home_location"] == {
        "type": "Point",
        "coordinates": [77.204, 28.614],
    }
    assert serialized["exclusion_zones"] == [{"type": "Polygon", "coordinates": [EXCLUSION_RING]}]


def test_saved_field_definition_trims_opaque_ids_and_nonblank_text() -> None:
    values = _valid_field_values()
    values.update(
        {
            "field_id": "  field_01  ",
            "sector_id": "  sector_01  ",
            "field_name": "  North Field  ",
            "crop_type": "  Wheat  ",
            "field_version": "  field-version-01  ",
        }
    )

    definition = SavedFieldDefinition.model_validate(values)

    assert definition.field_id == "field_01"
    assert definition.sector_id == "sector_01"
    assert definition.field_name == "North Field"
    assert definition.crop_type == "Wheat"
    assert definition.field_version == "field-version-01"


@pytest.mark.parametrize(
    "field_name",
    ["field_id", "sector_id", "field_name", "crop_type", "field_version"],
)
def test_saved_field_definition_rejects_missing_required_identity_or_metadata(
    field_name: str,
) -> None:
    values = _valid_field_values()
    del values[field_name]

    with pytest.raises(ValidationError):
        SavedFieldDefinition.model_validate(values)


@pytest.mark.parametrize(
    "field_name",
    ["field_id", "sector_id", "field_name", "crop_type", "field_version"],
)
def test_saved_field_definition_rejects_blank_identity_or_metadata(field_name: str) -> None:
    values = _valid_field_values()
    values[field_name] = "   "

    with pytest.raises(ValidationError):
        SavedFieldDefinition.model_validate(values)


def test_saved_field_definition_rejects_extra_fields_and_other_schema_versions() -> None:
    values = _valid_field_values()

    with pytest.raises(ValidationError):
        SavedFieldDefinition.model_validate({**values, "unexpected": True})
    with pytest.raises(ValidationError):
        SavedFieldDefinition.model_validate({**values, "schema_version": "2.0"})


def test_saved_field_definition_is_frozen_and_model_copy_revalidates() -> None:
    definition = SavedFieldDefinition.model_validate(_valid_field_values())

    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(definition, "field_name", "Changed")

    copied = definition.model_copy(update={"field_name": "  East Field  "}, deep=True)

    assert copied.field_name == "East Field"
    assert copied is not definition
    assert copied.field_boundary is not definition.field_boundary
    with pytest.raises(ValidationError):
        definition.model_copy(update={"field_version": "   "})


def test_saved_field_definition_defaults_to_no_exclusions() -> None:
    values = _valid_field_values()
    del values["exclusion_zones"]

    definition = SavedFieldDefinition.model_validate(values)

    assert definition.exclusion_zones == ()
