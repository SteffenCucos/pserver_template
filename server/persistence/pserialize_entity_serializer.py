
"""Entity serializer backed by the application's pserialize configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from typing import Any, TypeVar, cast

from models.base.id import Id

from .repository import EntitySerializer
from .serializing_middleware import (
    get_application_deserializer,
    get_application_serializer,
)


EntityT = TypeVar("EntityT")
Record = dict[str, Any]


class PSerializeEntitySerializer(EntitySerializer[EntityT]):
    """Convert entities to/from repository records using pserialize."""

    def __init__(self, class_type: type[EntityT]) -> None:
        self.class_type = class_type
        self.serializer = get_application_serializer()
        self.deserializer = get_application_deserializer()
        self.constructor_fields = _constructor_fields(class_type)

    def to_record(self, entity: EntityT) -> Record:
        record = self.serializer.serialize(entity)
        if hasattr(entity, "id") and "id" not in record:
            record["id"] = str(getattr(entity, "id"))
        return cast(Record, record)

    def from_record(self, record: Mapping[str, Any]) -> EntityT:
        record_dict = dict(record)
        constructor_record = {
            key: value
            for key, value in record_dict.items()
            if key in self.constructor_fields
        }
        entity = self.deserializer.deserialize(
            value=constructor_record,
            classType=self.class_type,
        )

        for key, value in record_dict.items():
            if key == "_id":
                setattr(entity, key, Id(str(value)))
            elif key not in self.constructor_fields:
                setattr(entity, key, value)

        return cast(EntityT, entity)


def _constructor_fields(class_type: type[Any]) -> set[str]:
    if not is_dataclass(class_type):
        return set()
    return {field.name for field in fields(class_type) if field.init}
