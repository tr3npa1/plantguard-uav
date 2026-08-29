"""Abstract persistence boundary for authoritative saved-field definitions."""

from typing import Protocol

from plantguard_uav.domain.field import SavedFieldDefinition
from plantguard_uav.domain.value_objects import OpaqueIdentifier


class FieldDefinitionRepository(Protocol):
    """Load selected field-sector definitions without exposing storage details."""

    async def get_definition(
        self,
        *,
        field_id: OpaqueIdentifier,
        sector_id: OpaqueIdentifier,
    ) -> SavedFieldDefinition | None:
        """Return the exact authoritative definition, or none when it does not exist."""
        ...
