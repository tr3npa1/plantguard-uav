"""Immutable saved-field contracts used during field-sector selection."""

from plantguard_uav.domain.geospatial import GeoJsonPoint, GeoJsonPolygon
from plantguard_uav.domain.value_objects import (
    SCHEMA_VERSION,
    ContractModel,
    NonBlankText,
    OpaqueIdentifier,
    SchemaVersion,
)


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
