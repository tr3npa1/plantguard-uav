"""Request dependencies for read-only field and inspection-configuration services."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import Request

from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.repositories.inspection_configuration import InspectionConfigurationSource
from plantguard_uav.repositories.sqlalchemy_fields import SqlAlchemyFieldDefinitionRepository
from plantguard_uav.services.field_catalogue import ListSavedFieldsService
from plantguard_uav.services.field_selection import GetFieldDefinitionService


def get_database_runtime(request: Request) -> DatabaseRuntime:
    """Obtain the shared runtime without opening a database connection."""
    return cast(DatabaseRuntime, request.app.state.database_runtime)


def get_inspection_configuration_source(request: Request) -> InspectionConfigurationSource | None:
    """Retrieve optional server wiring without file I/O or preempting request validation."""
    return cast(
        InspectionConfigurationSource | None,
        request.app.state.inspection_configuration_source,
    )


@asynccontextmanager
async def field_definition_service(
    runtime: DatabaseRuntime,
) -> AsyncIterator[GetFieldDefinitionService]:
    """Supply a lookup service within one caller-controlled transaction lifetime."""
    async with runtime.transaction() as session:
        repository = SqlAlchemyFieldDefinitionRepository(session)
        yield GetFieldDefinitionService(repository)


@asynccontextmanager
async def field_catalogue_service(
    runtime: DatabaseRuntime,
) -> AsyncIterator[ListSavedFieldsService]:
    """Supply a catalogue service inside one explicitly scoped transaction."""
    async with runtime.transaction() as session:
        repository = SqlAlchemyFieldDefinitionRepository(session)
        yield ListSavedFieldsService(repository)
