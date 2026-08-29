"""Process health endpoints for operators and container orchestration."""

from typing import Literal, cast

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict
from starlette import status

from plantguard_uav import __version__
from plantguard_uav.db import DatabaseRuntime

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Response returned when the API process is alive."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Response describing whether the API process can receive work."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "not_ready"]
    checks: dict[str, Literal["ready", "not_ready"]]


@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """Confirm that the HTTP process is alive and answering requests."""
    return HealthResponse(status="ok", service="plantguard-uav", version=__version__)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Report process and database readiness without claiming flight readiness."""
    process_ready = getattr(request.app.state, "ready", False) is True
    database_runtime = cast(DatabaseRuntime, request.app.state.database_runtime)
    database_health = await database_runtime.check_health()

    checks: dict[str, Literal["ready", "not_ready"]] = {
        "api_process": "ready" if process_ready else "not_ready",
        "database_connection": "ready" if database_health.connection_ready else "not_ready",
        "database_schema": "ready" if database_health.schema_ready else "not_ready",
    }
    ready = process_ready and database_health.ready
    readiness_status: Literal["ready", "not_ready"] = "ready" if ready else "not_ready"
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=readiness_status,
        checks=checks,
    )
