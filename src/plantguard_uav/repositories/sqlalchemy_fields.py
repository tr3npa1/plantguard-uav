"""SQLAlchemy adapter for authoritative saved-field definition reads."""

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from plantguard_uav.db.models import SavedFieldDefinitionRow
from plantguard_uav.domain.field import SavedFieldDefinition, SavedFieldSummary
from plantguard_uav.domain.value_objects import OpaqueIdentifier
from plantguard_uav.errors import PersistenceError

_OPERATION = "get_field_definition"


class SqlAlchemyFieldDefinitionRepository:
    """Read saved fields through a caller-owned asynchronous database session."""

    def __init__(self, session: AsyncSession) -> None:
        """Retain the session without taking ownership of its transaction."""
        self._session = session

    async def list_summaries(self, *, limit: int, offset: int) -> tuple[SavedFieldSummary, ...]:
        """Read only summary columns in stable composite-key order without caching."""
        statement = (
            select(
                SavedFieldDefinitionRow.field_id,
                SavedFieldDefinitionRow.sector_id,
                SavedFieldDefinitionRow.field_name,
                SavedFieldDefinitionRow.crop_type,
                SavedFieldDefinitionRow.field_version,
                SavedFieldDefinitionRow.schema_version,
            )
            .order_by(SavedFieldDefinitionRow.field_id, SavedFieldDefinitionRow.sector_id)
            .limit(limit)
            .offset(offset)
        )
        try:
            result = await self._session.execute(statement)
            summaries = []
            for row in result.mappings():
                summary = SavedFieldSummary.model_validate(row)
                # A listed identifier must address the same stored primary key on lookup.
                if summary.field_id != row["field_id"] or summary.sector_id != row["sector_id"]:
                    msg = "Stored field-sector identifiers must be canonical."
                    raise ValueError(msg)
                summaries.append(summary)
            return tuple(summaries)
        except SQLAlchemyError as exc:
            raise PersistenceError(
                context={"operation": "list_field_summaries", "reason": "database_error"}
            ) from exc
        except (TypeError, ValueError) as exc:
            raise PersistenceError(
                context={"operation": "list_field_summaries", "reason": "invalid_stored_data"}
            ) from exc

    async def get_definition(
        self,
        *,
        field_id: OpaqueIdentifier,
        sector_id: OpaqueIdentifier,
    ) -> SavedFieldDefinition | None:
        """Return a freshly validated definition for one exact identifier pair."""
        statement = select(*SavedFieldDefinitionRow.__table__.c).where(
            SavedFieldDefinitionRow.field_id == field_id,
            SavedFieldDefinitionRow.sector_id == sector_id,
        )
        try:
            result = await self._session.execute(statement)
            stored_definition = result.mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise PersistenceError(
                context={"operation": _OPERATION, "reason": "database_error"}
            ) from exc
        except (TypeError, ValueError) as exc:
            raise PersistenceError(
                context={"operation": _OPERATION, "reason": "invalid_stored_data"}
            ) from exc

        if stored_definition is None:
            return None

        try:
            return SavedFieldDefinition.model_validate(stored_definition)
        except ValidationError as exc:
            raise PersistenceError(
                context={"operation": _OPERATION, "reason": "invalid_stored_data"}
            ) from exc
