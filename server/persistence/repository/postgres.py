
"""Async Postgres implementation of the backend-neutral repository contract."""

from __future__ import annotations

import asyncio

from collections.abc import Mapping
from typing import Any

from psycopg import AsyncConnection, sql
from psycopg.rows import TupleRow

from .repository import EntityIdRequiredError, EntitySerializer, EntityT, Repository


class PostgresRepository(Repository[EntityT]):
    """Repository implementation backed by psycopg AsyncConnection."""

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
        self._connection: AsyncConnection[TupleRow] | None = None
        self._connection_lock = asyncio.Lock()

    async def create(self, entity: EntityT) -> EntityT:
        from psycopg.types.json import Jsonb

        connection = await self._get_connection()
        record = dict(self._serializer.to_record(entity))
        entity_id = self._extract_id(record)
        payload = self._payload_without_id(record)

        query = sql.SQL(
            "INSERT INTO {table} (id, {data_column}) "
            "VALUES (%s, %s) "
            "RETURNING id, {data_column}"
        ).format(
            table=sql.Identifier(self._table),
            data_column=sql.Identifier(self._data_column),
        )
        async with connection.cursor() as cursor:
            await cursor.execute(query, (entity_id, Jsonb(payload)))
            row = await cursor.fetchone()
        await connection.commit()
        return self._row_to_entity(row)

    async def get_by_id(self, entity_id: str) -> EntityT | None:
        row = await self._fetch_row(entity_id)
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
        query = sql.SQL(
            "SELECT id, {data_column} "
            "FROM {table} "
            "ORDER BY id ASC "
            "LIMIT {limit} OFFSET %s"
        ).format(
            table=sql.Identifier(self._table),
            data_column=sql.Identifier(self._data_column),
            limit=sql.Literal(limit) if limit > 0 else sql.SQL("ALL"),
        )
        async with connection.cursor() as cursor:
            await cursor.execute(query, (offset,))
            rows = await cursor.fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def update(self, entity_id: str, changes: Mapping[str, Any]) -> EntityT | None:
        from psycopg.types.json import Jsonb

        connection = await self._get_connection()
        existing = await self._fetch_row(entity_id)
        if existing is None:
            return None

        _, current_payload = existing
        updated_payload = dict(current_payload or {})
        updated_payload.update(
            {key: value for key, value in changes.items() if key != self.id_field}
        )

        query = sql.SQL(
            "UPDATE {table} "
            "SET {data_column} = %s "
            "WHERE id = %s "
            "RETURNING id, {data_column}"
        ).format(
            table=sql.Identifier(self._table),
            data_column=sql.Identifier(self._data_column),
        )
        async with connection.cursor() as cursor:
            await cursor.execute(query, (Jsonb(updated_payload), entity_id))
            row = await cursor.fetchone()
        await connection.commit()
        return self._row_to_entity(row)

    async def delete(self, entity_id: str) -> bool:
        connection = await self._get_connection()
        query = sql.SQL("DELETE FROM {table} WHERE id = %s").format(
            table=sql.Identifier(self._table),
        )
        async with connection.cursor() as cursor:
            await cursor.execute(query, (entity_id,))
            deleted_count = int(cursor.rowcount or 0)
        await connection.commit()
        return deleted_count > 0

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def _get_connection(self) -> AsyncConnection[TupleRow]:
        if self._connection is not None:
            return self._connection

        async with self._connection_lock:
            if self._connection is None:
                import psycopg

                self._connection = await psycopg.AsyncConnection.connect(self._uri)
                if self._ensure_table_on_connect:
                    await self._ensure_table()
        return self._connection

    async def _ensure_table(self) -> None:
        query = sql.SQL(
            "CREATE TABLE IF NOT EXISTS {table} ("
            "id TEXT PRIMARY KEY, "
            "{data_column} JSONB NOT NULL DEFAULT '{{}}'::jsonb"
            ")"
        ).format(
            table=sql.Identifier(self._table),
            data_column=sql.Identifier(self._data_column),
        )
        connection = await self._get_connection()
        async with connection.cursor() as cursor:
            await cursor.execute(query)
        await connection.commit()

    async def _fetch_row(self, entity_id: str) -> TupleRow | None:
        connection = await self._get_connection()
        query = sql.SQL("SELECT id, {data_column} FROM {table} WHERE id = %s").format(
            table=sql.Identifier(self._table),
            data_column=sql.Identifier(self._data_column),
        )
        async with connection.cursor() as cursor:
            await cursor.execute(query, (entity_id,))
            result: TupleRow | None = await cursor.fetchone()
            return result

    def _extract_id(self, record: Mapping[str, Any]) -> str:
        if self.id_field not in record:
            raise EntityIdRequiredError(f"entity record must include {self.id_field!r}")
        return str(record[self.id_field])

    def _payload_without_id(self, record: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in record.items() if key != self.id_field}

    def _row_to_entity(self, row: TupleRow | None) -> EntityT:
        if row is None:
            raise LookupError("expected database row, got None")

        entity_id, payload = row
        record = dict(payload or {})
        record[self.id_field] = entity_id
        return self._serializer.from_record(record)
