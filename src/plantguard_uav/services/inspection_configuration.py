"""Load inspection parameters and verify an explicitly requested identity."""

from pydantic import ConfigDict, ValidationError

from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration
from plantguard_uav.domain.value_objects import (
    SCHEMA_VERSION,
    ContractModel,
    OpaqueIdentifier,
    SchemaVersion,
)
from plantguard_uav.errors import InspectionConfigurationError
from plantguard_uav.repositories.inspection_configuration import InspectionConfigurationSource


class GetInspectionConfigurationQuery(ContractModel):
    """Require the exact configuration ID and revision expected by the caller."""

    model_config = ConfigDict(revalidate_instances="always")

    configuration_id: OpaqueIdentifier
    configuration_version: OpaqueIdentifier
    schema_version: SchemaVersion = SCHEMA_VERSION


class GetInspectionConfigurationService:
    """Check a fresh configuration from an injected source without selecting a fallback."""

    def __init__(self, source: InspectionConfigurationSource) -> None:
        """Retain the read-only source independently of its filesystem implementation."""
        self._source = source

    def execute(self, query: GetInspectionConfigurationQuery) -> InspectionFlightConfiguration:
        """Validate the query, load current parameters, and require matching identity."""
        query = GetInspectionConfigurationQuery.model_validate(query)
        loaded = self._source.load()
        try:
            configuration = InspectionFlightConfiguration.model_validate(loaded)
        except ValidationError:
            raise InspectionConfigurationError(reason="invalid_configuration") from None
        if (
            configuration.configuration_id != query.configuration_id
            or configuration.configuration_version != query.configuration_version
        ):
            raise InspectionConfigurationError(reason="identity_mismatch") from None
        return configuration
