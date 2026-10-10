"""Versioned inspection flight parameters, independent of flight-safety approval."""

from math import isfinite
from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, ConfigDict, Field, model_validator

from plantguard_uav.domain.value_objects import (
    SCHEMA_VERSION,
    ContractModel,
    OpaqueIdentifier,
    SchemaVersion,
)


def _validate_finite_number(value: object) -> float:
    """Accept finite JSON-style numbers without coercing text or booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = "Inspection parameters must contain only real numbers."
        raise ValueError(msg)
    try:
        number = float(value)
    except OverflowError as exc:
        msg = "Inspection parameters must be finite."
        raise ValueError(msg) from exc
    if not isfinite(number):
        msg = "Inspection parameters must be finite."
        raise ValueError(msg)
    return number


type _PositiveNumber = Annotated[
    float,
    BeforeValidator(_validate_finite_number),
    Field(gt=0),
]
type _OverlapFraction = Annotated[
    float,
    BeforeValidator(_validate_finite_number),
    Field(ge=0, lt=1),
]


class _InspectionConfigurationModel(ContractModel):
    """Revalidate existing instances when assembling nested inspection contracts."""

    model_config = ConfigDict(revalidate_instances="always")


class SurveyConfiguration(_InspectionConfigurationModel):
    """Require explicit survey AGL altitude, speed, and fractional image overlaps."""

    altitude_agl_m: _PositiveNumber
    speed_m_s: _PositiveNumber
    front_overlap_fraction: _OverlapFraction
    side_overlap_fraction: _OverlapFraction
    schema_version: SchemaVersion = SCHEMA_VERSION


class RevisitConfiguration(_InspectionConfigurationModel):
    """Require explicit revisit altitude in metres AGL and speed in metres/second."""

    altitude_agl_m: _PositiveNumber
    speed_m_s: _PositiveNumber
    schema_version: SchemaVersion = SCHEMA_VERSION


class InspectionFlightConfiguration(_InspectionConfigurationModel):
    """Group nominal survey/revisit inputs without representing a complete mission snapshot."""

    configuration_id: OpaqueIdentifier
    configuration_version: OpaqueIdentifier
    operating_environment: Literal["nominal_dry_daylight"]
    survey: SurveyConfiguration
    revisit: RevisitConfiguration
    schema_version: SchemaVersion = SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_revisit_altitude(self) -> Self:
        """Require nominal revisit AGL altitude to be below nominal survey AGL altitude."""
        if self.revisit.altitude_agl_m >= self.survey.altitude_agl_m:
            msg = "Revisit altitude AGL must be lower than survey altitude AGL."
            raise ValueError(msg)
        return self
