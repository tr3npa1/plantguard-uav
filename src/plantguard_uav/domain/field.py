"""Immutable saved-field contracts used during field-sector selection."""

from typing import Annotated, Final, Self

from pydantic import Field, StrictBool, model_validator

from plantguard_uav.domain.geospatial import GeoJsonPoint, GeoJsonPolygon
from plantguard_uav.domain.value_objects import (
    SCHEMA_VERSION,
    ContractModel,
    NonBlankText,
    OpaqueIdentifier,
    SchemaVersion,
)

MAX_FIELD_PAGE_OFFSET: Final = 2**63 - 1

type FieldPageLimit = Annotated[int, Field(strict=True, ge=1, le=100)]
type FieldPageOffset = Annotated[int, Field(strict=True, ge=0, le=MAX_FIELD_PAGE_OFFSET)]


class SavedFieldSummary(ContractModel):
    """Identify one saved field-sector choice without loading its geometry."""

    field_id: OpaqueIdentifier
    sector_id: OpaqueIdentifier
    field_name: NonBlankText
    crop_type: NonBlankText
    field_version: OpaqueIdentifier
    schema_version: SchemaVersion = SCHEMA_VERSION


class SavedFieldPage(ContractModel):
    """Return one bounded catalogue page without promising snapshot consistency."""

    items: tuple[SavedFieldSummary, ...]
    limit: FieldPageLimit = 20
    offset: FieldPageOffset = 0
    has_more: StrictBool
    schema_version: SchemaVersion = SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_page_size(self) -> Self:
        """Reject oversized pages and continuation flags on incomplete pages."""
        if len(self.items) > self.limit:
            msg = "A saved-field page cannot contain more items than its limit."
            raise ValueError(msg)
        if self.has_more and len(self.items) != self.limit:
            msg = "A saved-field page with more results must contain a full page."
            raise ValueError(msg)
        return self


class SavedFieldDefinition(ContractModel):
    """Describe one saved field and selected sector without mutating either."""

    field_id: OpaqueIdentifier
    sector_id: OpaqueIdentifier
    field_name: NonBlankText
    crop_type: NonBlankText
    field_boundary: GeoJsonPolygon
    sector_boundary: GeoJsonPolygon
    home_location: GeoJsonPoint
    exclusion_zones: tuple[GeoJsonPolygon, ...] = ()
    field_version: OpaqueIdentifier
    schema_version: SchemaVersion = SCHEMA_VERSION
