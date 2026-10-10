
from typing import Any, Callable

from .field import FieldMetadata
from .field import cfield as field


# Identity and nullability

PRIMARY_KEY = FieldMetadata(primary_key=True)
NULLABLE = FieldMetadata(nullable=True)
NOT_NULLABLE = FieldMetadata(nullable=False)
AUTOINCREMENT = FieldMetadata(autoincrement=True)

# Names and SQL types
def DB_NAME(name: str) -> FieldMetadata:
    return FieldMetadata(db_name=name)
def DB_TYPE(type_: str) -> FieldMetadata:
    return FieldMetadata(db_type=type_)
def LENGTH(value: int) -> FieldMetadata:
    return FieldMetadata(length=value)
def PRECISION(value: int) -> FieldMetadata:
    return FieldMetadata(precision=value)
def SCALE(value: int) -> FieldMetadata:
    return FieldMetadata(scale=value)
def COLLATION(value: str) -> FieldMetadata:
    return FieldMetadata(collation=value)

# Indexes and constraints
UNIQUE = FieldMetadata(unique=True)
def INDEX(name: str | None = None) -> FieldMetadata:
    return FieldMetadata(index=name or True)
def COMPOUND_INDEX(name: str) -> FieldMetadata:
    return FieldMetadata(compound_index=name)
TEXT_INDEX = FieldMetadata(text_index=True)
SPARSE = FieldMetadata(sparse=True)
def CHECK(expression: str) -> FieldMetadata:
    return FieldMetadata(check=expression)

# Validation constraints; translate to CHECK constraints where applicable
def MIN_LENGTH(value: int) -> FieldMetadata:
    return FieldMetadata(min_length=value)
def MAX_LENGTH(value: int) -> FieldMetadata:
    return FieldMetadata(max_length=value)
def MIN(value: int | float) -> FieldMetadata:
    return FieldMetadata(min=value)
def MAX(value: int | float) -> FieldMetadata:
    return FieldMetadata(max=value)
def PATTERN(value: str) -> FieldMetadata:
    return FieldMetadata(pattern=value)

# References and relationships
def FOREIGN_KEY(target: str) -> FieldMetadata:
    return FieldMetadata(foreign_key=target)
def RELATION(target: str) -> FieldMetadata:
    return FieldMetadata(relation=target)
def ON_DELETE(action: str) -> FieldMetadata:
    return FieldMetadata(on_delete=action)
def ON_UPDATE(action: str) -> FieldMetadata:
    return FieldMetadata(on_update=action)

# Defaults and generated values
def DEFAULT(value: Any) -> FieldMetadata:
    return FieldMetadata(default=value)
def DEFAULT_FACTORY(factory: Callable[[], Any]) -> FieldMetadata:
    return FieldMetadata(default_factory=factory)
def SERVER_DEFAULT(expression: str) -> FieldMetadata:
    return FieldMetadata(server_default=expression)
def ONUPDATE(expression: str) -> FieldMetadata:
    return FieldMetadata(onupdate=expression)

# Column behaviour
def COMMENT(value: str) -> FieldMetadata:
    return FieldMetadata(comment=value)
DEFERRED = FieldMetadata(deferred=True)
IMMUTABLE = FieldMetadata(immutable=True)

# Document/JSON-oriented storage
EMBEDDED = FieldMetadata(embedded=True)
SERIALIZED = FieldMetadata(serialized=True)
def TTL_SECONDS(value: int) -> FieldMetadata:
    return FieldMetadata(ttl_seconds=value)


__all__ = [
    "field"
]
