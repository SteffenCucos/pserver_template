
"""Async SQLite implementation of the backend-neutral repository contract."""

from __future__ import annotations

import json

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiosqlite

from .repository import EntityIdRequiredError, EntitySerializer, EntityT, Repository


_MEMORY_SQLITE_URIS = {":memory:", "sqlite:///:memory:"}
_SHARED_MEMORY_CONNECTIONS: dict[str, aiosqlite.Connection] = {}


class SQLiteRepository(Repository[EntityT]):
    """Repository implementation backed by aiosqlite."""

    def __init__(
        self,
        *,
        uri: str,
        table: str,
        serializer: EntitySerializer[EntityT],
        id_field: str = "id",
        data_column: str = "data",
        ensure_table: bool = True,
    ) -> None:
        self._uri = uri
        self._table = table
        self._serializer = serializer
        self.id_field = id_field
        self._data_column = data_column
        self._ensure_table_on_connect = ensure_table
        self._connection: aiosqlite.Connection | None = None
        self._owns_connection = uri not in _MEMORY_SQLITE_URIS
        self._table_ready = False

    async def create(self, entity: EntityT) -> EntityT:
        connection = await self._get_connection()
        record = dict(self._serializer.to_record(entity))
        entity_id = self._extract_id(record)
        payload = self._payload_without_id(record)

        cursor = await connection.execute(
            f'INSERT INTO "{self._table}" (id, "{self._data_column}") VALUES (?, ?)',
            (entity_id, json.dumps(payload, default=str)),
        )
        await cursor.close()
        await connection.commit()
        stored = await self.get_by_id(entity_id)
        if stored is None:
            raise LookupError("inserted entity could not be read back")
        return stored

    async def get_by_id(self, entity_id: str) -> EntityT | None:
        connection = await self._get_connection()
        cursor = await connection.execute(
            f'SELECT id, "{self._data_column}" FROM "{self._table}" WHERE id = ?',
            (entity_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return self._row_to_entity(row)

    async def find_one(self, condition: Mapping[str, Any]) -> EntityT | None:
        if not condition:
            entities = await self.enumerate(limit=1)
            return entities[0] if entities else None

        if len(condition) == 1:
            field, value = next(iter(condition.items()))
            if field in {self.id_field, "_id", "id"}:
                return await self.get_by_id(str(value))

        for entity in await self.enumerate():
            record = self._serializer.to_record(entity)
            if all(str(record.get(field)) == str(value) for field, value in condition.items()):
                return entity
        return None

    async def find_all(self, condition: Mapping[str, Any]) -> list[EntityT]:
        if not condition:
            return await self.enumerate()

        entities = await self.enumerate()
        matching: list[EntityT] = []
        for entity in entities:
            record = self._serializer.to_record(entity)
            if all(str(record.get(field)) == str(value) for field, value in condition.items()):
                matching.append(entity)
        return matching

    async def enumerate(self, *, limit: int = -1, offset: int = 0) -> list[EntityT]:
        connection = await self._get_connection()
        cursor = await connection.execute(
            f'SELECT id, "{self._data_column}" FROM "{self._table}" '
            "ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit if limit > 0 else -1, offset),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [self._row_to_entity(row) for row in rows]

    async def update(self, entity_id: str, changes: Mapping[str, Any]) -> EntityT | None:
        connection = await self._get_connection()
        current = await self.get_by_id(entity_id)
        if current is None:
            return None

        record = self._serializer.to_record(current)
        record.update(
            {key: value for key, value in changes.items() if key != self.id_field}
        )
        payload = self._payload_without_id(record)
        cursor = await connection.execute(
            f'UPDATE "{self._table}" SET "{self._data_column}" = ? WHERE id = ?',
            (json.dumps(payload, default=str), entity_id),
        )
        await cursor.close()
        await connection.commit()
        return await self.get_by_id(entity_id)

    async def delete(self, entity_id: str) -> bool:
        connection = await self._get_connection()
        cursor = await connection.execute(
            f'DELETE FROM "{self._table}" WHERE id = ?',
            (entity_id,),
        )
        deleted_count = int(cursor.rowcount or 0)
        await cursor.close()
        await connection.commit()
        return deleted_count > 0

    async def close(self) -> None:
        if self._connection is not None and self._owns_connection:
            await self._connection.close()
        self._connection = None
        self._table_ready = False

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            if self._uri in _MEMORY_SQLITE_URIS:
                connection = _SHARED_MEMORY_CONNECTIONS.get(self._uri)
                if connection is None:
                    connection = await aiosqlite.connect(":memory:")
                    connection.row_factory = aiosqlite.Row
                    _SHARED_MEMORY_CONNECTIONS[self._uri] = connection
                self._connection = connection
            else:
                self._connection = await aiosqlite.connect(_sqlite_path_from_uri(self._uri))
                self._connection.row_factory = aiosqlite.Row

        if self._ensure_table_on_connect and not self._table_ready:
            await self._ensure_table(self._connection)
            self._table_ready = True

        return self._connection

    async def _ensure_table(self, connection: aiosqlite.Connection) -> None:
        cursor = await connection.execute(
            f'CREATE TABLE IF NOT EXISTS "{self._table}" ('
            f'id TEXT PRIMARY KEY, "{self._data_column}" TEXT NOT NULL DEFAULT "{{}}")'
        )
        await cursor.close()
        await connection.commit()

    def _extract_id(self, record: Mapping[str, Any]) -> str:
        if self.id_field not in record:
            raise EntityIdRequiredError(f"entity record must include {self.id_field!r}")
        return str(record[self.id_field])

    def _payload_without_id(self, record: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in record.items() if key != self.id_field}

    def _row_to_entity(self, row: aiosqlite.Row) -> EntityT:
        payload = json.loads(row[self._data_column] or "{}")
        record = dict(payload)
        record[self.id_field] = row["id"]
        return self._serializer.from_record(record)


def _sqlite_path_from_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme != "sqlite":
        return uri

    path = parsed.path
    if path.startswith("/") and not path.startswith("//"):
        path = path[1:]

    db_path = Path(path)
    if db_path.parent != Path(""):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)
