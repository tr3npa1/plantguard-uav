"""Safe HTTP exception handling for the PlantGuard UAV API."""

from typing import cast
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from plantguard_uav.errors import PlantGuardError
from plantguard_uav.logging import get_logger


async def handle_plantguard_error(request: Request, exc: Exception) -> JSONResponse:
    """Turn a known application error into a stable, safe JSON response."""
    error = cast(PlantGuardError, exc)
    get_logger(__name__).warning(
        "request_failed",
        method=request.method,
        path=request.url.path,
        error_code=error.error_code,
        status_code=error.status_code,
        context=error.context,
    )
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.error_code,
                "message": error.public_message,
            }
        },
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic response for an unexpected error and record a trace ID."""
    error_id = uuid4().hex
    get_logger(__name__).error(
        "unexpected_request_failure",
        method=request.method,
        path=request.url.path,
        error_id=error_id,
        exception_type=type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred.",
                "error_id": error_id,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide known and unexpected exception handlers."""
    app.add_exception_handler(PlantGuardError, handle_plantguard_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
