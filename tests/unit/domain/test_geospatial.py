from math import inf, nan

from pydantic import TypeAdapter, ValidationError
import pytest

from plantguard_uav.domain import (
    GeoJsonLinearRing,
    GeoJsonPoint,
    GeoJsonPolygon,
    Wgs84Position,
)

POSITION_ADAPTER: TypeAdapter[Wgs84Position] = TypeAdapter(Wgs84Position)
RING_ADAPTER: TypeAdapter[GeoJsonLinearRing] = TypeAdapter(GeoJsonLinearRing)

OUTER_RING = [
    [77.20, 28.61],
    [77.21, 28.61],
    [77.21, 28.62],
    [77.20, 28.61],
]
HOLE_RING = [
    [77.202, 28.612],
    [77.204, 28.612],
    [77.204, 28.614],
    [77.202, 28.612],
]


def _set_attribute(instance: object, attribute: str, value: object) -> None:
    setattr(instance, attribute, value)


def test_point_serializes_as_exact_two_dimensional_geojson() -> None:
    point = GeoJsonPoint.model_validate({"coordinates": [77.209, 28.6139]})

    assert point.coordinates == (77.209, 28.6139)
    assert point.model_dump(mode="json") == {
        "type": "Point",
        "coordinates": [77.209, 28.6139],
    }
    assert "schema_version" not in point.model_dump()


def test_polygon_serializes_positions_and_rings_as_geojson_arrays() -> None:
    polygon = GeoJsonPolygon.model_validate({"coordinates": [OUTER_RING, HOLE_RING]})

    assert isinstance(polygon.coordinates, tuple)
    assert all(isinstance(ring, tuple) for ring in polygon.coordinates)
    assert all(isinstance(position, tuple) for ring in polygon.coordinates for position in ring)
    assert polygon.model_dump(mode="json") == {
        "type": "Polygon",
        "coordinates": [OUTER_RING, HOLE_RING],
    }


@pytest.mark.parametrize(
    "position",
    [
        [-180, -90],
        [-180, 90],
        [180, -90],
        [180, 90],
        [0, 0],
    ],
)
def test_position_accepts_inclusive_wgs84_limits(position: list[int]) -> None:
    validated = POSITION_ADAPTER.validate_python(position)

    assert validated == (float(position[0]), float(position[1]))


@pytest.mark.parametrize(
    "position",
    [
        [],
        [77.2],
        [77.2, 28.6, 100.0],
        "77.2,28.6",
        {77.2, 28.6},
    ],
)
def test_position_rejects_wrong_or_unordered_containers(position: object) -> None:
    with pytest.raises(ValidationError, match="exactly longitude and latitude"):
        POSITION_ADAPTER.validate_python(position)


@pytest.mark.parametrize(
    "position",
    [
        ["77.2", 28.6],
        [77.2, "28.6"],
        [True, 28.6],
        [77.2, False],
    ],
)
def test_position_rejects_non_numeric_or_boolean_components(position: object) -> None:
    with pytest.raises(ValidationError, match="only real numbers"):
        POSITION_ADAPTER.validate_python(position)


@pytest.mark.parametrize(
    "position",
    [
        [nan, 28.6],
        [inf, 28.6],
        [-inf, 28.6],
        [77.2, nan],
        [77.2, inf],
        [10**400, 28.6],
    ],
)
def test_position_rejects_non_finite_components(position: object) -> None:
    with pytest.raises(ValidationError, match="finite"):
        POSITION_ADAPTER.validate_python(position)


@pytest.mark.parametrize(
    ("position", "message"),
    [
        ([-180.0001, 0], "Longitude"),
        ([180.0001, 0], "Longitude"),
        ([0, -90.0001], "Latitude"),
        ([0, 90.0001], "Latitude"),
    ],
)
def test_position_rejects_values_outside_wgs84_limits(position: list[float], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        POSITION_ADAPTER.validate_python(position)


@pytest.mark.parametrize(
    ("ring", "message"),
    [
        ([[0, 0], [1, 0], [0, 0]], "at least four"),
        ([[0, 0], [1, 0], [1, 1], [0, 1]], "starting position"),
        ([[0, 0], [1, 0], [0, 0], [0, 0]], "three distinct"),
        ([[0, 0], [1, 0], [1, 0], [0, 1], [0, 0]], "consecutive duplicate"),
    ],
)
def test_ring_rejects_invalid_structural_geometry(ring: list[list[int]], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        RING_ADAPTER.validate_python(ring)


def test_ring_rejects_a_non_array_container() -> None:
    with pytest.raises(ValidationError, match="ordered coordinate array"):
        RING_ADAPTER.validate_python("not-a-coordinate-array")


@pytest.mark.parametrize("coordinates", [[], ()])
def test_polygon_rejects_an_empty_ring_collection(coordinates: object) -> None:
    with pytest.raises(ValidationError):
        GeoJsonPolygon(coordinates=coordinates)  # type: ignore[arg-type]


def test_geometry_is_frozen_and_model_copy_revalidates_updates() -> None:
    point = GeoJsonPoint.model_validate({"coordinates": [77.209, 28.6139]})

    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(point, "coordinates", (0.0, 0.0))

    unchanged = point.model_copy()
    deep_copy = point.model_copy(deep=True)
    copied = point.model_copy(update={"coordinates": [0, 0]}, deep=True)

    assert unchanged == point
    assert unchanged is not point
    assert deep_copy == point
    assert deep_copy is not point
    assert copied == GeoJsonPoint(coordinates=(0.0, 0.0))
    assert copied is not point
    with pytest.raises(ValidationError):
        point.model_copy(update={"coordinates": [181, 0]})


def test_wrong_geojson_type_and_extra_members_are_rejected() -> None:
    with pytest.raises(ValidationError):
        GeoJsonPoint.model_validate({"type": "Polygon", "coordinates": [0, 0]})
    with pytest.raises(ValidationError):
        GeoJsonPoint.model_validate({"type": "Point", "coordinates": [0, 0], "crs": "EPSG:4326"})
