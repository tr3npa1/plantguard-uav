"""FastAPI application factory and startup lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI

from plantguard_uav import __version__
from plantguard_uav.api.exception_handlers import register_exception_handlers
from plantguard_uav.api.routes.fields import router as fields_router
from plantguard_uav.api.routes.health import router as health_router
from plantguard_uav.api.routes.inspection_configuration import (
    router as inspection_configuration_router,
)
from plantguard_uav.config import Environment, Settings, load_settings
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.logging import configure_logging, get_logger
from plantguard_uav.repositories.inspection_configuration import InspectionConfigurationSource


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Mark the process ready during its managed startup-to-shutdown lifetime."""
    settings = cast(Settings, app.state.settings)
    database_runtime = cast(DatabaseRuntime, app.state.database_runtime)
    logger = get_logger(__name__)
    try:
        logger.info(
            "application_started",
            environment=settings.environment.value,
            version=__version__,
        )
        app.state.ready = True
        yield
    finally:
        app.state.ready = False
        try:
            await database_runtime.dispose()
        finally:
            logger.info("application_stopped")


def create_app(
    settings: Settings | None = None,
    database_runtime: DatabaseRuntime | None = None,
    *,
    inspection_configuration_source: InspectionConfigurationSource | None = None,
) -> FastAPI:
    """Build a side-effect-controlled application with injected or loaded settings."""
    resolved_settings = settings if settings is not None else load_settings()
    resolved_database_runtime = (
        database_runtime
        if database_runtime is not None
        else DatabaseRuntime.from_settings(resolved_settings.database)
    )
    configure_logging(resolved_settings.log_level, resolved_settings.log_format)

    production = resolved_settings.environment is Environment.PRODUCTION
    app = FastAPI(
        title="PlantGuard UAV",
        version=__version__,
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
        lifespan=application_lifespan,
    )
    app.state.settings = resolved_settings
    app.state.database_runtime = resolved_database_runtime
    app.state.inspection_configuration_source = inspection_configuration_source
    app.state.ready = False
    app.include_router(health_router)
    # Field and inspection-configuration access require authorization before production exposure.
    if resolved_settings.environment in {Environment.DEVELOPMENT, Environment.TESTING}:
        app.include_router(fields_router)
        app.include_router(inspection_configuration_router)
    register_exception_handlers(app)
    return app
