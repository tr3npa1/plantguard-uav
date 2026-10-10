from pydantic import ValidationError
import pytest

from plantguard_uav.domain import GeoJsonPoint, GeoJsonPolygon, SavedFieldDefinition
from plantguard_uav.domain.field import (
    MAX_FIELD_PAGE_OFFSET,
    SavedFieldPage,
    SavedFieldSummary,
)

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


def _valid_summary_values() -> dict[str, object]:
    return {
        "field_id": "field_01",
        "sector_id": "sector_01",
        "field_name": "North Field",
        "crop_type": "Wheat",
        "field_version": "field-version-01",
    }


def test_saved_field_summary_contains_only_normalized_metadata() -> None:
    values = {name: f"  {value}  " for name, value in _valid_summary_values().items()}

    summary = SavedFieldSummary.model_validate(values)

    assert summary.model_dump(mode="json") == {
        **_valid_summary_values(),
        "schema_version": "1.0",
    }


@pytest.mark.parametrize(
    "field_name",
    ["field_id", "sector_id", "field_name", "crop_type", "field_version"],
)
def test_saved_field_summary_requires_all_identity_and_metadata(field_name: str) -> None:
    values = _valid_summary_values()
    del values[field_name]

    with pytest.raises(ValidationError):
        SavedFieldSummary.model_validate(values)


@pytest.mark.parametrize(
    "field_name",
    ["field_id", "sector_id", "field_name", "crop_type", "field_version"],
)
@pytest.mark.parametrize("invalid_value", ["", " \t ", b"text", 42, None])
def test_saved_field_summary_rejects_blank_or_nonstring_metadata(
    field_name: str,
    invalid_value: object,
) -> None:
    values = {**_valid_summary_values(), field_name: invalid_value}

    with pytest.raises(ValidationError):
        SavedFieldSummary.model_validate(values)


@pytest.mark.parametrize(
    "extra_values",
    [
        {"unexpected": True},
        {"schema_version": "2.0"},
        {"field_boundary": {"type": "Polygon", "coordinates": [FIELD_RING]}},
    ],
)
def test_saved_field_summary_rejects_extra_fields_geometry_and_other_versions(
    extra_values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        SavedFieldSummary.model_validate({**_valid_summary_values(), **extra_values})


def test_saved_field_summary_is_frozen_and_copies_are_revalidated() -> None:
    summary = SavedFieldSummary.model_validate(_valid_summary_values())

    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(summary, "field_name", "Changed")

    copied = summary.model_copy(update={"field_name": "  East Field  "}, deep=True)

    assert copied is not summary
    assert copied.field_name == "East Field"
    assert summary.field_name == "North Field"
    with pytest.raises(ValidationError):
        summary.model_copy(update={"sector_id": "   "})


def test_saved_field_page_defaults_and_json_shape() -> None:
    summary = SavedFieldSummary.model_validate(_valid_summary_values())
    input_items = [summary]

    page = SavedFieldPage.model_validate({"items": input_items, "has_more": False})
    input_items.clear()

    assert page.items == (summary,)
    assert isinstance(page.items, tuple)
    assert page.model_dump(mode="json") == {
        "items": [{**_valid_summary_values(), "schema_version": "1.0"}],
        "limit": 20,
        "offset": 0,
        "has_more": False,
        "schema_version": "1.0",
    }


@pytest.mark.parametrize("limit", [1, 20, 100])
def test_saved_field_page_accepts_empty_pages_and_valid_limits(limit: int) -> None:
    page = SavedFieldPage(items=(), limit=limit, offset=MAX_FIELD_PAGE_OFFSET, has_more=False)

    assert page.items == ()
    assert page.limit == limit
    assert page.offset == MAX_FIELD_PAGE_OFFSET
    assert page.has_more is False


@pytest.mark.parametrize(
    ("name", "invalid_value"),
    [
        ("limit", 0),
        ("limit", 101),
        ("limit", True),
        ("limit", 20.0),
        ("limit", "20"),
        ("offset", -1),
        ("offset", MAX_FIELD_PAGE_OFFSET + 1),
        ("offset", False),
        ("offset", 0.0),
        ("offset", "0"),
        ("has_more", 1),
        ("has_more", "false"),
        ("has_more", None),
        ("schema_version", "2.0"),
        ("unexpected", True),
    ],
)
def test_saved_field_page_rejects_invalid_pagination_flags_and_metadata(
    name: str,
    invalid_value: object,
) -> None:
    values = {"items": (), "has_more": False, name: invalid_value}

    with pytest.raises(ValidationError):
        SavedFieldPage.model_validate(values)


@pytest.mark.parametrize("missing_name", ["items", "has_more"])
def test_saved_field_page_requires_items_and_more_flag(missing_name: str) -> None:
    values: dict[str, object] = {"items": (), "has_more": False}
    del values[missing_name]

    with pytest.raises(ValidationError):
        SavedFieldPage.model_validate(values)


def test_saved_field_page_revalidates_summary_contents() -> None:
    invalid_summary = {**_valid_summary_values(), "crop_type": "   "}

    with pytest.raises(ValidationError):
        SavedFieldPage.model_validate({"items": [invalid_summary], "has_more": False})


def test_saved_field_page_rejects_more_items_than_its_limit() -> None:
    summary = SavedFieldSummary.model_validate(_valid_summary_values())
    second = summary.model_copy(update={"sector_id": "sector_02"})

    with pytest.raises(ValidationError):
        SavedFieldPage(items=(summary, second), limit=1, has_more=False)


@pytest.mark.parametrize("item_count", [0, 1])
def test_saved_field_page_requires_a_full_page_when_more_rows_exist(item_count: int) -> None:
    summary = SavedFieldSummary.model_validate(_valid_summary_values())

    with pytest.raises(ValidationError):
        SavedFieldPage(items=(summary,) * item_count, limit=2, has_more=True)


def test_saved_field_page_accepts_a_full_page_with_more_rows() -> None:
    summary = SavedFieldSummary.model_validate(_valid_summary_values())

    page = SavedFieldPage(items=(summary,), limit=1, has_more=True)

    assert page.has_more is True


def test_saved_field_page_is_deeply_frozen_and_copy_revalidates_page_shape() -> None:
    summary = SavedFieldSummary.model_validate(_valid_summary_values())
    page = SavedFieldPage(items=(summary,), limit=1, has_more=True)

    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(page, "items", ())
    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(page.items[0], "field_name", "Changed")
    with pytest.raises(ValidationError):
        page.model_copy(update={"items": ()})
    with pytest.raises(ValidationError):
        page.model_copy(update={"offset": -1})

    copied = page.model_copy(update={"has_more": False}, deep=True)

    assert copied is not page
    assert copied.items[0] is not page.items[0]
    assert copied.has_more is False
    assert page.has_more is True
