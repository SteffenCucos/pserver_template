
"""Backend-neutral repository contracts.

The Repository is the application interface to the underlying database. It
exposes only application concepts and primitive Python values, while concrete
backend implementations own all driver-specific concerns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, Generic, TypeVar


EntityT = TypeVar("EntityT")
Record = dict[str, Any]


class EntitySerializer(ABC, Generic[EntityT]):
    """Convert between application entities and plain persistence records."""

    @abstractmethod
    def to_record(self, entity: EntityT) -> Record:
        """Convert an application entity to a backend-neutral record."""
        raise NotImplementedError

    @abstractmethod
    def from_record(self, record: Record) -> EntityT:
        """Convert a backend-neutral record to an application entity."""
        raise NotImplementedError


class MappingSerializer(EntitySerializer[Record]):
    """Pass-through serializer for apps that use dict records directly."""

    def to_record(self, entity: Record) -> Record:
        return entity

    def from_record(self, record: Record) -> Record:
        return record


class Repository(ABC, Generic[EntityT]):
    """Minimal async CRUD contract shared by every storage backend."""

    @abstractmethod
    async def create(self, entity: EntityT) -> EntityT:
        """Persist a new entity and return the stored entity."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> EntityT | None:
        """Return one entity by public id, or None when not found."""
        raise NotImplementedError

    @abstractmethod
    async def find_one(self, condition: Mapping[str, Any]) -> EntityT | None:
        """Return one entity matching a primitive equality condition."""
        raise NotImplementedError

    @abstractmethod
    async def find_all(self, condition: Mapping[str, Any]) -> list[EntityT]:
        """Return all entities matching a primitive equality condition."""
        raise NotImplementedError

    @abstractmethod
    async def enumerate(self, *, limit: int = -1, offset: int = 0) -> list[EntityT]:
        """Return entities in deterministic backend order."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, entity_id: str, changes: Mapping[str, Any]) -> EntityT | None:
        """Patch primitive field values and return the updated entity."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete one entity by public id and return whether anything changed."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Release backend resources held by this repository."""
        raise NotImplementedError


class RepositoryError(RuntimeError):
    """Base exception for repository failures."""


class EntityIdRequiredError(RepositoryError):
    """Raised when an entity cannot be persisted because it has no id field."""
