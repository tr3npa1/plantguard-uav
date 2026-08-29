"""Strict immutable GeoJSON values for WGS 84 field geometry."""

from collections.abc import Mapping
from copy import deepcopy
from itertools import pairwise
from math import isfinite
from typing import Annotated, Any, Literal, Self

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field


def _validate_real_number(value: object) -> float:
    """Accept only finite JSON-style numbers and normalize them to floats."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = "WGS 84 coordinates must contain only real numbers."
        raise ValueError(msg)
    try:
        coordinate = float(value)
    except OverflowError as exc:
        msg = "WGS 84 coordinates must be finite."
        raise ValueError(msg) from exc
    if not isfinite(coordinate):
        msg = "WGS 84 coordinates must be finite."
        raise ValueError(msg)
    return coordinate


type _FiniteCoordinate = Annotated[float, BeforeValidator(_validate_real_number)]


def _validate_position_container(value: object) -> object:
    """Require an ordered two-dimensional GeoJSON position container."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        msg = "A WGS 84 position must contain exactly longitude and latitude."
        raise ValueError(msg)
    return value


def _validate_position_range(position: tuple[float, float]) -> tuple[float, float]:
    """Enforce valid longitude and latitude ranges in GeoJSON axis order."""
    longitude, latitude = position
    if not -180.0 <= longitude <= 180.0:
        msg = "Longitude must be between -180 and 180 degrees."
        raise ValueError(msg)
    if not -90.0 <= latitude <= 90.0:
        msg = "Latitude must be between -90 and 90 degrees."
        raise ValueError(msg)
    return position


type Wgs84Position = Annotated[
    tuple[_FiniteCoordinate, _FiniteCoordinate],
    BeforeValidator(_validate_position_container),
    AfterValidator(_validate_position_range),
]


def _validate_ring_container(value: object) -> object:
    """Require an ordered GeoJSON coordinate-array container."""
    if not isinstance(value, (list, tuple)):
        msg = "A GeoJSON linear ring must be an ordered coordinate array."
        raise ValueError(msg)
    return value


def _validate_linear_ring(ring: tuple[Wgs84Position, ...]) -> tuple[Wgs84Position, ...]:
    """Enforce structural, but not topological, GeoJSON ring validity."""
    if len(ring) < 4:
        msg = "A GeoJSON linear ring must contain at least four positions."
        raise ValueError(msg)
    if ring[0] != ring[-1]:
        msg = "A GeoJSON linear ring must end at its starting position."
        raise ValueError(msg)
    if len(set(ring[:-1])) < 3:
        msg = "A GeoJSON linear ring must contain at least three distinct positions."
        raise ValueError(msg)
    if any(current == following for current, following in pairwise(ring)):
        msg = "A GeoJSON linear ring must not contain consecutive duplicate positions."
        raise ValueError(msg)
    return ring


type GeoJsonLinearRing = Annotated[
    tuple[Wgs84Position, ...],
    BeforeValidator(_validate_ring_container),
    AfterValidator(_validate_linear_ring),
]


class _GeoJsonModel(BaseModel):
    """Provide strict immutable behavior without adding non-GeoJSON members."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        validate_default=True,
    )

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        """Return a new geometry after revalidating original and updated members."""
        values = self.model_dump(round_trip=True)
        if deep:
            values = deepcopy(values)
        if update:
            values.update(deepcopy(dict(update)) if deep else update)
        return type(self).model_validate(values)


class GeoJsonPoint(_GeoJsonModel):
    """Represent one two-dimensional WGS 84 GeoJSON Point geometry."""

    type: Literal["Point"] = "Point"
    coordinates: Wgs84Position


class GeoJsonPolygon(_GeoJsonModel):
    """Represent a structurally valid WGS 84 GeoJSON Polygon geometry."""

    type: Literal["Polygon"] = "Polygon"
    coordinates: tuple[GeoJsonLinearRing, ...] = Field(min_length=1)
