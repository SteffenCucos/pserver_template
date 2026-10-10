
"""Factory for selecting a concrete repository backend."""

from __future__ import annotations

from typing import TypeVar

from ..config import DatabaseBackend, DatabaseSettings
from ..repository import EntitySerializer, Repository


EntityT = TypeVar("EntityT")


def create_repository(
    *,
    settings: DatabaseSettings,
    resource_name: str,
    serializer: EntitySerializer[EntityT],
    id_field: str = "id",
) -> Repository[EntityT]:
    """Create a repository for the configured backend.

    resource_name maps to a Mongo collection for Mongo and to a SQL table for
    Postgres/SQLite. The returned object satisfies the backend-neutral
    Repository protocol.
    """
    if settings.backend == DatabaseBackend.MONGO:
        from .mongo import MongoRepository

        return MongoRepository(
            uri=settings.uri,
            database=settings.database,
            collection=resource_name,
            serializer=serializer,
            id_field=id_field,
        )

    if settings.backend == DatabaseBackend.POSTGRES:
        from .postgres import PostgresRepository

        return PostgresRepository(
            uri=settings.uri,
            table=resource_name,
            serializer=serializer,
            id_field=id_field,
        )

    if settings.backend == DatabaseBackend.SQLITE:
        from .sqlite import SQLiteRepository

        return SQLiteRepository(
            uri=settings.uri,
            table=resource_name,
            serializer=serializer,
            id_field=id_field,
        )

    raise ValueError(f"unsupported database backend: {settings.backend}")
