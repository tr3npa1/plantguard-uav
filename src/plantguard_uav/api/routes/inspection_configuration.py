"""Read-only HTTP access to one server-configured inspection input."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from plantguard_uav.api.dependencies import get_inspection_configuration_source
from plantguard_uav.api.exception_handlers import ApiErrorResponse
from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration
from plantguard_uav.domain.value_objects import OpaqueIdentifier
from plantguard_uav.errors import InspectionConfigurationUnavailableError
from plantguard_uav.repositories.inspection_configuration import InspectionConfigurationSource
from plantguard_uav.services.inspection_configuration import (
    GetInspectionConfigurationQuery,
    GetInspectionConfigurationService,
)

router = APIRouter(prefix="/api/v1/inspection-configuration", tags=["inspection-configuration"])


@router.get(
    "",
    response_model=InspectionFlightConfiguration,
    responses={
        422: {
            "model": ApiErrorResponse,
            "description": "Required identifiers are invalid or missing.",
        },
        500: {
            "model": ApiErrorResponse,
            "description": "Configuration loading, identity verification, or another operation failed.",
        },
        503: {
            "model": ApiErrorResponse,
            "description": "No inspection configuration source is configured for this application.",
        },
    },
)
def get_inspection_configuration(
    configuration_id: Annotated[
        OpaqueIdentifier, Query(description="The expected configuration ID.")
    ],
    configuration_version: Annotated[
        OpaqueIdentifier, Query(description="The exact expected configuration revision.")
    ],
    response: Response,
    source: Annotated[
        InspectionConfigurationSource | None, Depends(get_inspection_configuration_source)
    ],
) -> InspectionFlightConfiguration:
    """Verify fresh server-selected parameters in a worker thread without approving flight."""
    query = GetInspectionConfigurationQuery(
        configuration_id=configuration_id,
        configuration_version=configuration_version,
    )
    if source is None:
        raise InspectionConfigurationUnavailableError
    configuration = GetInspectionConfigurationService(source).execute(query)
    response.headers["Cache-Control"] = "no-store"
    return configuration
