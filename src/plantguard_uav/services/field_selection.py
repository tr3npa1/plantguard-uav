"""Read-only application service for authoritative saved-field selection."""

from plantguard_uav.domain.field import SavedFieldDefinition
from plantguard_uav.domain.value_objects import (
    SCHEMA_VERSION,
    ContractModel,
    OpaqueIdentifier,
    SchemaVersion,
)
from plantguard_uav.errors import FieldNotFoundError, PersistenceError
from plantguard_uav.repositories.fields import FieldDefinitionRepository


class GetFieldDefinitionQuery(ContractModel):
    """Identify one versioned saved-field sector to load."""

    field_id: OpaqueIdentifier
    sector_id: OpaqueIdentifier
    schema_version: SchemaVersion = SCHEMA_VERSION


class GetFieldDefinitionService:
    """Load fresh authoritative field data through an injected repository."""

    def __init__(self, repository: FieldDefinitionRepository) -> None:
        """Store the abstract repository used by each independent query."""
        self._repository = repository

    async def execute(self, query: GetFieldDefinitionQuery) -> SavedFieldDefinition:
        """Return one exact definition without caching or changing domain state."""
        definition = await self._repository.get_definition(
            field_id=query.field_id,
            sector_id=query.sector_id,
        )
        if definition is None:
            raise FieldNotFoundError(
                context={
                    "field_id": query.field_id,
                    "sector_id": query.sector_id,
                }
            )
        if definition.field_id != query.field_id or definition.sector_id != query.sector_id:
            raise PersistenceError(
                context={
                    "operation": "get_field_definition",
                    "reason": "identity_mismatch",
                }
            )
        return definition
