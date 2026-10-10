"""Read-only application query for discovering saved field-sector choices."""

from plantguard_uav.domain.field import FieldPageLimit, FieldPageOffset, SavedFieldPage
from plantguard_uav.domain.value_objects import ContractModel
from plantguard_uav.repositories.fields import FieldCatalogueRepository


class ListSavedFieldsQuery(ContractModel):
    """Validate bounded pagination before opening a catalogue transaction."""

    limit: FieldPageLimit = 20
    offset: FieldPageOffset = 0


class ListSavedFieldsService:
    """Build catalogue pages using one extra row to detect further results."""

    def __init__(self, repository: FieldCatalogueRepository) -> None:
        """Retain the catalogue interface without taking transaction ownership."""
        self._repository = repository

    async def execute(self, query: ListSavedFieldsQuery) -> SavedFieldPage:
        """Read a fresh page of summaries without modifying saved definitions."""
        summaries = await self._repository.list_summaries(
            limit=query.limit + 1,
            offset=query.offset,
        )
        return SavedFieldPage(
            items=summaries[: query.limit],
            limit=query.limit,
            offset=query.offset,
            has_more=len(summaries) > query.limit,
        )
