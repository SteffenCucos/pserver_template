
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime as Datetime
from typing import Any, Generic, TypeVar, cast

from persistence.repository import Repository
from persistence.serializing_middleware import get_application_serializer

from models.base.entity import IdEntity
from models.base.id import Id


TEntity = TypeVar("TEntity", bound=IdEntity)


class EntityDAO(Generic[TEntity]):
    """Repository-facing DAO for DB-backed entities."""

    def __init__(self, repository: Repository[TEntity]) -> None:
        self.repository = repository
        self.serializer = get_application_serializer()

    async def create(self, entity: TEntity) -> TEntity:
        self.prep_for_save(entity)
        return await self.repository.create(entity)

    async def save(self, entity: TEntity) -> Id:
        return (await self.create(entity)).id

    async def save_many(self, entities: list[TEntity]) -> list[Id]:
        return [await self.save(entity) for entity in entities]

    async def get_by_id(self, entity_id: Id) -> TEntity | None:
        return await self.repository.get_by_id(str(entity_id))

    async def find_one_by_id(self, entity_id: Id) -> TEntity | None:
        return await self.get_by_id(entity_id)

    async def find_one(self, condition: Mapping[str, Any]) -> TEntity | None:
        return await self.repository.find_one(condition)

    async def find_all(self, condition: Mapping[str, Any]) -> list[TEntity]:
        return await self.repository.find_all(condition)

    async def enumerate(self, *, limit: int = -1, offset: int = 0) -> list[TEntity]:
        return await self.repository.enumerate(limit=limit, offset=offset)

    async def update(
        self,
        entity_id: Id,
        changes: Mapping[str, Any],
    ) -> TEntity | None:
        update_record = dict(changes)
        update_record.setdefault("_updated_date", Datetime.now().isoformat())
        return await self.repository.update(str(entity_id), update_record)

    async def update_entity(self, entity: TEntity) -> TEntity | None:
        self.prep_for_save(entity)
        update_record = cast(dict[str,Any], self.serializer.serialize(entity))
        update_record.pop("_id", None)
        return await self.repository.update(str(entity.id), update_record)

    async def update_many(self, entities: list[TEntity]) -> list[TEntity | None]:
        return [await self.update_entity(entity) for entity in entities]

    async def delete(self, entity_id: Id) -> bool:
        return await self.repository.delete(str(entity_id))

    async def delete_by_id(self, entity_id: Id) -> bool:
        return await self.delete(entity_id)

    async def close(self) -> None:
        await self.repository.close()

    def prep_for_save(self, entity: TEntity) -> None:
        self.validate_has_id(entity)
        if not hasattr(entity, "created_date"):
            entity.set_created_date()
        entity.set_updated_date()

    def validate_has_id(self, entity: TEntity) -> None:
        if not hasattr(entity, "id"):
            raise ValueError("Entity must have id")
