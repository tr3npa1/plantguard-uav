"""Abstract persistence boundary for authoritative saved-field definitions."""

from typing import Protocol

from plantguard_uav.domain.field import SavedFieldDefinition, SavedFieldSummary
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


class FieldCatalogueRepository(Protocol):
    """List ordered field-sector summaries independently of detail lookups."""

    async def list_summaries(self, *, limit: int, offset: int) -> tuple[SavedFieldSummary, ...]:
        """Read at most limit rows in field-ID/sector-ID order, allowing lookahead."""
        ...
