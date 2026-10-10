"""Read-only HTTP access to authoritative saved-field definitions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from plantguard_uav.api.dependencies import (
    field_catalogue_service,
    field_definition_service,
    get_database_runtime,
)
from plantguard_uav.api.exception_handlers import ApiErrorResponse
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.domain.field import MAX_FIELD_PAGE_OFFSET, SavedFieldDefinition, SavedFieldPage
from plantguard_uav.domain.value_objects import OpaqueIdentifier
from plantguard_uav.services.field_catalogue import ListSavedFieldsQuery
from plantguard_uav.services.field_selection import GetFieldDefinitionQuery

router = APIRouter(prefix="/api/v1/fields", tags=["fields"])


@router.get(
    "",
    response_model=SavedFieldPage,
    responses={
        422: {"model": ApiErrorResponse, "description": "Pagination parameters are invalid."},
        500: {
            "model": ApiErrorResponse,
            "description": "Storage or another server operation failed.",
        },
    },
)
async def list_saved_fields(
    response: Response,
    runtime: Annotated[DatabaseRuntime, Depends(get_database_runtime)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum summaries to return.")] = 20,
    offset: Annotated[
        int, Query(ge=0, le=MAX_FIELD_PAGE_OFFSET, description="Ordered summaries to skip.")
    ] = 0,
) -> SavedFieldPage:
    """Discover field-sector choices without certifying geometry or flight readiness."""
    query = ListSavedFieldsQuery(limit=limit, offset=offset)
    async with field_catalogue_service(runtime) as service:
        page = await service.execute(query)

    response.headers["Cache-Control"] = "no-store"
    return page


@router.get(
    "/definition",
    response_model=SavedFieldDefinition,
    responses={
        404: {"model": ApiErrorResponse, "description": "The saved field sector was not found."},
        422: {
            "model": ApiErrorResponse,
            "description": "Required identifiers are invalid or missing.",
        },
        500: {
            "model": ApiErrorResponse,
            "description": "Storage or another server operation failed.",
        },
    },
)
async def get_field_definition(
    field_id: Annotated[OpaqueIdentifier, Query(description="The saved field identifier.")],
    sector_id: Annotated[OpaqueIdentifier, Query(description="The saved sector identifier.")],
    response: Response,
    runtime: Annotated[DatabaseRuntime, Depends(get_database_runtime)],
) -> SavedFieldDefinition:
    """Load one saved sector without selecting it or changing mission state."""
    query = GetFieldDefinitionQuery(field_id=field_id, sector_id=sector_id)
    async with field_definition_service(runtime) as service:
        definition = await service.execute(query)

    response.headers["Cache-Control"] = "no-store"
    return definition
