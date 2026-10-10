
"""Async Mongo implementation of the backend-neutral repository contract."""

from __future__ import annotations

import asyncio

from collections.abc import Mapping
from threading import Lock
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo_inmemory import MongoClient

from .repository import EntityIdRequiredError, EntitySerializer, EntityT, Repository


MEMORY_MONGO_URIS = {
    "memory://",
    "mongo://memory",
    "mongodb://memory",
    "mongodb://in-memory",
}
_SHARED_MEMORY_SERVERS: dict[str, MongoClient] = {}
_MEMORY_SERVER_LOCK = Lock()


class MongoRepository(Repository[EntityT]):
    """Repository implementation backed by PyMongo's native async API."""

    def __init__(
        self,
        *,
        uri: str,
        database: str,
        collection: str,
        serializer: EntitySerializer[EntityT],
        id_field: str = "id",
    ) -> None:
        self._uri = uri
        self._database = database
        self._collection_name = collection
        self._serializer = serializer
        self.id_field = id_field
        self._client: AsyncMongoClient[Mapping[str, Any]] | None = None
        self._collection: AsyncCollection[Mapping[str, Any]] | None = None

    async def create(self, entity: EntityT) -> EntityT:
        collection = await self._get_collection()
        record = self._to_backend_record(self._serializer.to_record(entity))
        await collection.insert_one(record)
        return self._from_backend_record(record)

    async def get_by_id(self, entity_id: str) -> EntityT | None:
        collection = await self._get_collection()
        record = await collection.find_one({"_id": entity_id})
        if record is None:
            return None
        return self._from_backend_record(record)

    async def find_one(self, condition: Mapping[str, Any]) -> EntityT | None:
        collection = await self._get_collection()
        record = await collection.find_one(self._to_backend_condition(condition))
        if record is None:
            return None
        return self._from_backend_record(record)

    async def find_all(self, condition: Mapping[str, Any]) -> list[EntityT]:
        collection = await self._get_collection()
        cursor = collection.find(self._to_backend_condition(condition)).sort("_id", 1)
        records = await cursor.to_list(None)
        return [self._from_backend_record(record) for record in records]

    async def enumerate(self, *, limit: int = -1, offset: int = 0) -> list[EntityT]:
        collection = await self._get_collection()
        cursor = collection.find({}).sort("_id", 1).skip(offset)
        if limit > 0:
            cursor = cursor.limit(limit)
        records = await cursor.to_list(None)
        return [self._from_backend_record(record) for record in records]

    async def update(self, entity_id: str, changes: Mapping[str, Any]) -> EntityT | None:
        from pymongo import ReturnDocument

        update_record = self._to_backend_patch(changes)
        if not update_record:
            return await self.get_by_id(entity_id)

        collection = await self._get_collection()
        record = await collection.find_one_and_update(
            {"_id": entity_id},
            {"$set": update_record},
            return_document=ReturnDocument.AFTER,
        )
        if record is None:
            return None
        return self._from_backend_record(record)

    async def delete(self, entity_id: str) -> bool:
        collection = await self._get_collection()
        result = await collection.delete_one({"_id": entity_id})
        deleted_count = int(result.deleted_count or 0)
        return deleted_count > 0

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._collection = None

    async def _get_collection(self) -> AsyncCollection[Mapping[str, Any]]:
        if self._collection is not None:
            return self._collection

        from pymongo import AsyncMongoClient

        uri = self._uri
        if uri in MEMORY_MONGO_URIS:
            server = await asyncio.to_thread(_get_memory_mongo_server, uri)
            address = server.address
            if address is None:
                raise RuntimeError("in-memory mongod did not report an address")
            host, port = address
            uri = f"mongodb://{host}:{port}"

        self._client = AsyncMongoClient(uri)
        self._collection = self._client[self._database][self._collection_name]
        return self._collection

    def _to_backend_record(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        backend_record = dict(record)
        if "_id" in backend_record:
            backend_record["_id"] = str(backend_record["_id"])
            return backend_record

        if self.id_field not in backend_record:
            raise EntityIdRequiredError(f"entity record must include {self.id_field!r}")

        backend_record["_id"] = str(backend_record.pop(self.id_field))
        return backend_record

    def _to_backend_patch(self, changes: Mapping[str, Any]) -> Mapping[str, Any]:
        patch = dict(changes)
        if self.id_field in patch:
            patch["_id"] = str(patch.pop(self.id_field))
        if "_id" in patch:
            patch.pop("_id")
        return patch

    def _to_backend_condition(self, condition: Mapping[str, Any]) -> Mapping[str, Any]:
        query = dict(condition)
        if self.id_field in query:
            query["_id"] = str(query.pop(self.id_field))
        if "_id" in query:
            query["_id"] = str(query["_id"])
        return query

    def _from_backend_record(self, record: Mapping[str, Any]) -> EntityT:
        public_record = dict(record)
        if "_id" in public_record:
            public_record[self.id_field] = str(public_record.pop("_id"))
        return self._serializer.from_record(public_record)


def _get_memory_mongo_server(uri: str) -> MongoClient:
    """Start one ephemeral mongod for test-only memory URIs."""
    with _MEMORY_SERVER_LOCK:
        if uri not in _SHARED_MEMORY_SERVERS:
            from pymongo_inmemory import MongoClient

            client = MongoClient()
            client.admin.command("ping")
            _SHARED_MEMORY_SERVERS[uri] = client
        return _SHARED_MEMORY_SERVERS[uri]
