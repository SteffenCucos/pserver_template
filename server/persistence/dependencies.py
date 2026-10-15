
"""FastAPI dependency providers for repository injection."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TypeVar

from fastapi import Depends

from .config import DatabaseSettings
from .repository import EntitySerializer, Repository
from .repository.factory import create_repository


EntityT = TypeVar("EntityT")


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings.from_env()


def repository_dependency(
    *,
    resource_name: str,
    serializer: EntitySerializer[EntityT],
    id_field: str = "id",
) -> Callable[..., AsyncIterator[Repository[EntityT]]]:
    """
    Returns a method used during dependency injection that resolves a repository of the correct resource
    """
    async def get_repository(
        settings: DatabaseSettings = Depends(get_database_settings),
    ) -> AsyncIterator[Repository[EntityT]]:
        repository = create_repository(
            settings=settings,
            resource_name=resource_name,
            serializer=serializer,
            id_field=id_field,
        )
        try:
            yield repository
        finally:
            await repository.close()

    return get_repository
