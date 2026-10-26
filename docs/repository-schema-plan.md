# Repository Schema Plan

## Goal

Replace the document-style storage in `PostgresRepository` and `SQLiteRepository`:

```text
id TEXT + data JSON/JSONB
```

with typed tables generated from the entity classes by the schema code in
`server/persistence/repository/sql/`. Mongo keeps its document storage.

There is no SQL data to preserve, so this is a clean cutover. This plan replaces the
SQLAlchemy/Alembic approach in `typed-sql-schema-plan.md`.

## Where things stand

- **Entities** are dataclasses. `IdEntity` declares `id`, `created_date` and
  `updated_date`, and fields carry metadata from `persistence.models`, such as
  `PRIMARY_KEY`, `UNIQUE`, `INDEX`, `FOREIGN_KEY` and `CHECK`.
- **Schema generation:**
  - `parse_entities_to_tables` turns entity classes into `TableNode`s.
  - `PostgresTypeRewriter` and `SqliteTypeRewriter` map column types.
  - `PostgresVisitor` emits `CREATE TABLE` plus a later `ALTER TABLE` for constraints.
    `SqliteVisitor` puts constraints inside `CREATE TABLE` and emits indexes as separate
    statements.
  - `generate_schema_ddl_operations` (Postgres only) is called by tests, not by the app.
- **Repositories** store `(id, data)` and create their own table the first time they
  connect (`_ensure_table`). `find_one` and `find_all` load the whole table and filter in
  Python.
- **Records** come from `PSerializeEntitySerializer.to_record`. Datetimes are ISO
  strings, booleans are `bool` and ids are `str`.

## Problems the plan has to handle

The first three were confirmed by running the code against Postgres 16 and SQLite.

1. **The type rewriters change the original columns.** After
   `SqliteTypeRewriter.rewrite(table)`, the input table's `created_date` is `TEXT` instead
   of `TIMESTAMP`, and `email_verified` is `INTEGER` instead of `BOOLEAN`. The
   repositories need the original types to convert values, for example to tell a
   boolean column from an integer one.
2. **Postgres constraint order depends on entity order.** With `[UserRole, User, Role]`,
   the foreign key from `user_roles` to `users` is added before `users` has its primary
   key, and Postgres rejects it with `InvalidForeignKey`.
3. **The DDL can't run twice.** The second run fails with `DuplicateTable`. Table
   creation will run on every app start, and the API tests start a new app for each test
   against one shared Postgres database.
4. **Two table names don't match.** Repositories are created with `perms` and
   `role_perms`, but the entities declare `permissions` and `role_permissions`.
5. **The health check reads a table with no entity.** `HealthService` opens a repository
   on `health`.
6. **Old field names are still in use.** `EntityDAO.update` writes `_updated_date`,
   `EntityDAO.update_entity` removes `_id`, and `PSerializeEntitySerializer.from_record`
   special-cases `_id`. With typed columns, `_updated_date` is an unknown column.
7. **Deleting a user who has roles will fail.** `user_roles.user_id` references
   `users.id`, but the user delete route only removes sessions first.

## Work plan

The app keeps working at the end of each stage. Use the API tests as the check after
every stage: `pytest test-scafold/tests` runs every test against Mongo, SQLite and
Postgres, and `APP_DB_BACKEND=sqlite pytest test-scafold/tests` runs one backend.

### 1. Rewire callers (storage stays `id + data`)

This stage changes which table each repository uses and how queries are called, so
later stages only touch the repositories.

1. **Fix the old field names.** `EntityDAO.update` writes `updated_date`,
   `update_entity` removes `id`, and the `_id` branch in
   `PSerializeEntitySerializer.from_record` goes.
2. **Keep one list of entities.** Add
   `ENTITY_TYPES = [User, Permission, Role, UserRole, RolePermission, Session]` next to
   the startup code in `server/main.py`.
   - `parse_entities_to_tables` needs all of them in one call, because it resolves
     foreign keys across the list.
   - If the list moves to its own top-level module, add that module to
     `_clear_scaffold_modules` in the API test conftest. Otherwise later tests keep
     entity classes from an earlier test's import.
3. **Create repositories from an entity type.** `repository_dependency(entity_type=User)`
   builds the serializer itself and takes the table or collection name from
   `User.table_name()`. Remove the `resource_name` and `id_field` parameters.
   - This fixes the `perms`/`role_perms` mismatch.
   - Mongo collection names change too (`perms` becomes `permissions`).
4. **Make the health check a ping.** Add `ping(settings)` next to the repository
   factory, with one version per backend: `SELECT 1` for SQL and `admin.command("ping")`
   for Mongo. `HealthService` calls it instead of reading a table.
5. **Stop filtering lists in Python.** `RolePermissionDAO`, `UserRoleDAO` and
   `SessionDAO.list_for_user` call `enumerate()` and filter the result. Switch them to
   `find_all({"role_id": ...})` and so on.

Done when the API tests and unit tests pass.

### 2. Make the schema code safe to run on every startup

All changes are in `server/persistence/repository/sql/`.

1. **Make the rewriters work on a copy.** Start `TableRewriter.rewrite` with
   `table = copy.deepcopy(table)`. A deep copy keeps the primary key, index and
   constraint nodes pointing at the copied columns. Add a test that the input table is
   unchanged.
2. **Only create what's missing.** Both visitors emit `CREATE TABLE IF NOT EXISTS` and
   `CREATE INDEX IF NOT EXISTS`.
3. **Emit each Postgres constraint as its own named statement.**
   - `PostgresVisitor.rewrite` returns the create statements plus a list of
     `(constraint_name, statement)` pairs, one `ALTER TABLE ... ADD CONSTRAINT` each.
   - Postgres has no `ADD CONSTRAINT IF NOT EXISTS`, so the startup code skips names
     already in `pg_constraint`.
   - Constraint names are fixed (`pk_`, `uq_`, `fk_` or `chk_` plus table and column),
     so matching on name is reliable.
4. **Order the statements across all tables.** Replace
   `generate_schema_ddl_operations` with `generate_schema_ddl(tables, backend)`,
   returning one flat list:
   - **Postgres:** all tables, then all indexes, then all primary keys and unique
     constraints, then all foreign keys, then all checks.
   - **SQLite:** each table with its constraints inline, followed by its indexes. Table
     order doesn't matter in SQLite.

Done when the generated DDL runs twice in a row against an empty database on both
backends, including with the entities in the order `[UserRole, User, Role]`.

### 3. Create the schema at startup and switch SQLite

1. **Add a startup hook.** Add a FastAPI `lifespan` to `server/main.py` that:
   - parses `ENTITY_TYPES` once;
   - stores the tables on `app.state.schema`;
   - runs the DDL (SQLite only in this stage).

   The repository dependency reads the table from `request.app.state.schema`. If an
   entity isn't in the list, it raises an error saying to add it to `ENTITY_TYPES`.
   `TestClient(main.app)` runs the lifespan, so the API tests cover it.
2. **Use one SQLite connect function.** Move the connection logic out of
   `SQLiteRepository._get_connection` into a module-level function used by both the
   repository and the startup code.
   - An in-memory database only exists on that one shared connection, so both have to
     use it.
   - The function runs `PRAGMA foreign_keys = ON` immediately after connecting, before
     any other statement. SQLite doesn't enforce foreign keys without it, and ignores
     the setting inside an open transaction.
3. **Convert values between records and columns.** Build a small converter from the
   original table, not the rewritten one. That's why the copy in stage 2 matters.

   | Column type (before rewriting) | Value in the record | In SQLite | In Postgres |
   |---|---|---|---|
   | `TIMESTAMP` / `DATE` / `TIME` | ISO string | ISO string | `datetime`, converted to and from ISO |
   | `BOOLEAN` | `bool` | `0`/`1`, converted back to `bool` | `bool` |
   | `JSON` | `dict` / `list` | `json.dumps` / `json.loads` | `Jsonb(...)` / `dict` |
   | `TEXT`, `INTEGER`, `DOUBLE PRECISION` | unchanged | unchanged | unchanged |

4. **Rewrite the `SQLiteRepository` queries against the table's columns.** Check every
   field name against the column list and raise a new `UnknownFieldError(RepositoryError)`
   for anything else. Only then put the names in double quotes in the SQL.

   | Method | SQL |
   |---|---|
   | `create` | `INSERT INTO t (cols) VALUES (?, ...) RETURNING cols` |
   | `get_by_id` | `SELECT cols FROM t WHERE <pk> = ?` |
   | `find_one` / `find_all` | `WHERE a = ? AND b = ?`, ordered by primary key; `find_one` adds `LIMIT 1` |
   | `enumerate` | `ORDER BY <pk> LIMIT ? OFFSET ?` |
   | `update` | `UPDATE t SET a = ?, ... WHERE <pk> = ? RETURNING cols` |
   | `delete` | as now, using the primary key column |

   - In `find_one` and `find_all`, use `IS NULL` when a value is `None`, and drop the
     special case for `_id`/`id`. The primary key is just another column.
   - In `update`, remove the primary key from `changes`. If nothing is left to set,
     return `get_by_id` instead.
   - Get the primary key name from `table.primary_key.columns[0].name`.
   - Remove `data_column`, `ensure_table` and `_ensure_table`.
   - `RETURNING` needs SQLite 3.35 or later.

Done when `APP_DB_BACKEND=sqlite pytest test-scafold/tests` passes. Postgres still uses
`id + data` at this point, so its tests should still pass too.

### 4. Switch Postgres

1. Use the same queries as SQLite, built with `psycopg.sql.Identifier`. Pass
   `row_factory=dict_row` when connecting so each row comes back keyed by column name.
2. Run the stage 2 statements at startup, skipping constraint names already in
   `pg_constraint`.
3. Wrap each write in `async with connection.transaction():` instead of calling
   `commit()`. After an error, a psycopg connection rejects every later statement until
   it's rolled back. The context manager does the rollback, which matters once unique
   and foreign key violations can happen.
4. Remove `data_column` and `ensure_table`.

Done when the API tests pass on all three backends.

### 5. Constraints, errors and tests

1. **Turn constraint errors into repository errors.** Catch
   `psycopg.errors.UniqueViolation`, `psycopg.errors.ForeignKeyViolation` and
   `sqlite3.IntegrityError`, and re-raise them as `DuplicateEntityError` or
   `ConstraintViolationError` (both subclasses of `RepositoryError`). The services
   already check for duplicates first. This catches what they miss, such as two requests
   at once, and returns a clear error instead of a 500.
2. **Delete a user's roles before the user.** The route already deletes sessions first.
   See the decision below.
3. **Optional extra constraints:** `UNIQUE` on `User.user_name` (the service already
   rejects duplicates) and a foreign key on `Session.user_id`.
4. **Tests:**
   - **Unit:** the rewriter copy, statement order, running the DDL twice, and value
     conversion in both directions on each backend (bool, timestamp, JSON, `None`).
   - **Repository tests on SQLite and Postgres:** move the `postgres_uri` fixture out of
     the API test conftest into a shared root `conftest.py` so `tests/` can use it too.
   - **API:** deleting a user who has roles, and filtering by an unknown field.
   - **Existing tests:** update the expected DDL strings in
     `tests/persistence/repository/sql/test_schema.py` and the visitor tests.

## Decision: rows that point at a deleted row

**Recommended:** delete related rows in the service. Deleting a user also deletes their
`user_roles` and sessions. Leave the foreign keys at the default `NO ACTION`, so on SQL a
forgotten cleanup fails loudly instead of leaving orphaned rows. Mongo has no foreign
keys, so cleanup in the service is the only way all three backends behave the same.

**Alternative:** `ON DELETE CASCADE`. The `ON_DELETE` field metadata exists, but
`ForeignKeyNode`, the parser and both visitors would need to support it, and Mongo would
still leave the orphaned rows behind.

## Out of scope

- **Changing an entity later.** The startup code only creates what's missing, so adding
  a field to an entity won't add the column to an existing table. That needs migrations
  eventually. Fresh and in-memory databases are fine.
- **Connection reuse.** Each repository still opens its own Postgres connection per
  request. A connection pool is a separate change.
- **Quoting names in the DDL.** The visitors don't quote table or column names, so a
  field named after a reserved word (`order`, `user`) would break `CREATE TABLE`. It's a
  small fix to make while working in that code.
