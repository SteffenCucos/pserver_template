# Typed SQL Schema Plan

## Goal

Change the PostgreSQL and SQLite repositories from document-style storage:

```text
id + data JSON/JSONB
```

to tables whose columns are defined by entity classes and their dataclass
fields. MongoDB remains document-oriented and keeps its current behavior.

There is no existing SQL data to preserve, so this is a clean schema cutover.

## Design decisions

- Keep the existing domain models as Python dataclasses.
- Make `IdEntity` a dataclass so its inherited ID and audit attributes are
  discoverable by dataclass schema inspection.
- Keep `_id` as the Python-side identifier for compatibility with current DAOs,
  serializers, and MongoDB. Map it to the physical SQL column `id`.
- Use `typing.Annotated` for optional SQL-specific field metadata, while
  `dataclasses.field()` continues to control constructor/default behavior.
- Map ordinary supported Python field types automatically. Require explicit
  metadata for constraints and other database-specific behavior.
- Use SQLAlchemy Core for shared schema metadata and portable SQL statements;
  retain the repository/DAO interfaces and application dataclasses.
- Add Alembic as the production schema lifecycle mechanism. Optionally retain
  automatic schema creation only for in-memory SQLite tests and local dev.

## Target model shape

```python
from dataclasses import dataclass, field
from datetime import datetime as Datetime
from typing import Annotated


@dataclass
class IdEntity:
    _id: Id = field(init=False, repr=False)
    _created_date: Datetime = field(init=False, repr=False)
    _updated_date: Datetime = field(init=False, repr=False)


@dataclass
class User(Entity()):
    user_name: Annotated[str, sql_column(unique=True, index=True)]
    password_hash: str
    email: Annotated[str, sql_column(unique=True, index=True)]
    email_verified: bool = False
```

`Annotated` describes SQL mapping. `field()` describes dataclass behavior; both
can be used on the same attribute when needed:

```python
_id: Annotated[Id, sql_column(name="id", primary_key=True)] = field(
    init=False,
    repr=False,
)
```

The schema layer may instead apply the standard mapping for `_id`,
`_created_date`, and `_updated_date` centrally, so every entity does not need
to repeat those annotations.

## Initial SQL mapping

| Python field | SQL column | PostgreSQL | SQLite |
|---|---|---|---|
| `_id: Id` | `id` | `TEXT PRIMARY KEY` | `TEXT PRIMARY KEY` |
| `_created_date: datetime` | `created_date` | `TIMESTAMP NOT NULL` | `DATETIME NOT NULL` |
| `_updated_date: datetime` | `updated_date` | `TIMESTAMP NOT NULL` | `DATETIME NOT NULL` |
| `str` | field name | `TEXT` | `TEXT` |
| `bool` | field name | `BOOLEAN` | `BOOLEAN` |
| `int` | field name | `BIGINT` | `INTEGER` |
| `float` | field name | `DOUBLE PRECISION` | `REAL` |
| `datetime` | field name | `TIMESTAMP` | `DATETIME` |
| `T | None` | field name | matching type, nullable | matching type, nullable |

Unsupported values such as lists, dictionaries, arbitrary objects, and unions
other than `T | None` must initially fail schema generation with a clear error.
They can later be supported deliberately through an explicit JSON column type.

## Work plan

### 1. Make persistence fields discoverable

Update `models.base.entity.IdEntity` to be a dataclass and declare `_id`,
`_created_date`, and `_updated_date` with `init=False`.

Preserve `Entity()` and its current deterministic-ID behavior initially so
existing model declarations such as `Role(Entity("name"))` remain valid.

Acceptance criteria:

- `dataclasses.fields(User)` includes the inherited persistence fields.
- Constructing a new entity still assigns its ID and audit timestamps.
- `PSerializeEntitySerializer` still restores persisted IDs and timestamps.
- MongoDB serialization and round trips remain unchanged.

### 2. Define a schema metadata API

Create a small SQL schema module, for example `db/sql_schema.py`, containing:

- a `sql_column(...)` metadata marker;
- a model/table declaration mechanism, such as `@sql_table("users")`;
- a dataclass-inspection function using `get_type_hints(..., include_extras=True)`;
- validation for duplicate columns, unsupported types, invalid identifiers, and
  conflicting options;
- a type mapper that emits SQLAlchemy Core `Column` objects.

Metadata must cover at least:

- SQL column name override;
- nullable/not-null override;
- primary key;
- unique constraint;
- index;
- foreign key;
- server/default value where required.

Acceptance criteria:

- Each current entity produces a deterministic SQLAlchemy `Table`.
- `_id` maps to the `id` primary-key column.
- Python field names are retained for records while physical column aliases are
  handled by the mapping layer.

### 3. Declare the first-class tables

Register tables for `User`, `Permission`, `Role`, `UserRole`,
`RolePermission`, and `Session`.

Apply explicit constraints where domain behavior already implies them:

- `User.user_name`: unique and indexed;
- `User.email`: unique and indexed;
- `Role.name`: primary/deterministic ID and unique as appropriate;
- `UserRole.user_id` and `UserRole.role_id`: foreign keys and a composite
  unique constraint;
- `RolePermission.role_id` and `RolePermission.permission_id`: foreign keys
  and a composite unique constraint;
- `Session.user_id`: foreign key and index;
- `Session.expires_at`: index if session cleanup/querying requires it.

The exact foreign-key delete policy (`RESTRICT`, `CASCADE`, or explicit
application deletes) must be chosen before the initial migration is created.

### 4. Replace the SQL repository storage implementation

Replace the `id + data` assumptions in `PostgresRepository` and
`SQLiteRepository` with shared schema-aware operations:

- `create`: insert every mapped column;
- `get_by_id`: select mapped columns by `id`;
- `enumerate`: select mapped columns with ordering, limit, and offset;
- `find_one` / `find_all`: compile validated equality predicates into SQL;
- `update`: validate mapped change fields and issue an SQL `UPDATE` for those
  columns;
- row hydration: translate physical SQL column names back into serializer
  record names before calling `from_record`.

Repository methods must not interpolate field names or user-supplied values
into SQL. Table/column objects and bound parameters must be used throughout.

Acceptance criteria:

- No SQL table has a `data` JSON/TEXT payload column.
- `find_one` and `find_all` filter in the database.
- Unknown query/update fields fail clearly rather than silently filtering in
  Python.
- PostgreSQL and SQLite produce the same repository-level results.

### 5. Add schema lifecycle management

Add SQLAlchemy and Alembic dependencies and configure a single application
metadata registry containing all SQL tables.

Create the initial Alembic revision from the complete typed schema. Apply it to
fresh PostgreSQL and SQLite databases in tests.

Define the runtime rule:

- production: apply Alembic migrations before starting the application;
- local development: optionally provide an explicit bootstrap command;
- tests: create schema directly from metadata for isolated in-memory SQLite
  tests, or apply migrations where migration coverage is required.

Remove the SQL repositories' runtime `CREATE TABLE IF NOT EXISTS` behavior
once the bootstrap/test policy is in place.

### 6. Test the cutover

Add source-level repository tests; the test tree currently has no checked-in
SQLite/PostgreSQL repository test source despite compiled test artifacts.

Cover both SQL dialects for:

- generated schema columns, nullability, indexes, unique constraints, and
  foreign keys;
- entity create/read/update/delete;
- SQL-side lookup by every supported field type;
- pagination and deterministic ordering;
- optional field and datetime round trips;
- duplicate/foreign-key failures;
- unknown field validation;
- serializer hydration of IDs and audit fields.

Add a Mongo regression test confirming that the `IdEntity` dataclass change
does not alter document records or entity round trips.

## Delivery sequence

1. Implement `IdEntity` dataclass fields and Mongo regression coverage.
2. Build metadata/type mapping and prove it with `User` on SQLite.
3. Convert both SQL repositories and add backend-parity tests.
4. Register all application entities and add constraints/foreign keys.
5. Add Alembic and generate the initial schema revision.
6. Update README configuration and model-authoring documentation.

## Explicit non-goals for the first version

- Migrating or backfilling existing JSON-backed SQL data.
- Automatic schema alteration at repository startup.
- Arbitrary nested-object/list persistence without explicit JSON mapping.
- ORM relationship loading or replacing the existing DAO/repository boundary.
- Changing MongoDB into a relational model.

## Estimated effort

| Milestone | Estimate |
|---|---:|
| Schema proof of concept (`User` + SQLite) | 2–4 days |
| Full repository conversion and SQL parity tests | 4–7 days |
| All current entities, constraints, and Alembic setup | 3–6 days |
| Documentation and integration verification | 1–2 days |

Expected total for a template-quality implementation: approximately 2–4 weeks,
depending primarily on the desired constraint/delete semantics and PostgreSQL
test environment.
