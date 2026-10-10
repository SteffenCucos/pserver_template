# pserver_template
A FastAPI server template with pre-built application structure, asynchronous backend-neutral persistence, authentication/RBAC support, and a CLI scaffolder.

Use this repository as a starting point for small API services that need a clean baseline layout instead of starting from an empty FastAPI project.

## Features

- FastAPI application structure with async DB-backed request paths.
- Organized API, service, auth, user, model, and persistence modules.
- Centralized exception handling pattern.
- CLI scaffolder that clones this template into a new app folder.
- Entity-rooted DB model convention with `_id`, `_created_date`, and `_updated_date` on DB-backed models.
- Async backend-neutral repository contract with Mongo, Postgres, and SQLite implementations.
- Native async persistence drivers: PyMongo `AsyncMongoClient`, psycopg async connections, and `aiosqlite`.
- Entity DAOs that wrap repositories directly and keep shared entity lifecycle rules in one place.
- FastAPI-native dependency providers for repositories, DAOs, and services.
- Route authentication and permission annotations enforced through FastAPI dependency injection.
- User passwords are hashed with Argon2id through an injected password service and are excluded from API responses.

## Scaffold a new app

Install the CLI from GitHub:

```bash
pipx install git+https://github.com/SteffenCucos/Server_Template.git
```

Or install it into your current Python environment:

```bash
pip install git+https://github.com/SteffenCucos/Server_Template.git
```

Create a new app:

```bash
server-template new billing-api
```

This creates `./billing-api`, clones the template, removes the cloned `.git` directory, rewrites the package name, and removes the scaffolder files from the generated app.

Useful options:

```bash
server-template new billing-api --target-dir ./services/billing-api
server-template new billing-api --package-name billing_service
server-template new billing-api --keep-git
server-template new billing-api --keep-cli
server-template new billing-api --force
```

You can also run the CLI as a module from a checkout of this repo:

```bash
python -m server_template new billing-api
```

## Async persistence architecture

The template keeps database-specific code at the bottom of the dependency graph and propagates async I/O upward through DAOs, services, and DB-backed endpoints:

```text
Async endpoint / dependency
  -> Service
    -> DAO
      -> Repository[TEntity]
        -> MongoRepository | PostgresRepository | SQLiteRepository
```

All actual database operations are awaitable. Pure local work such as serialization, model mutation, and permission-tree evaluation remains synchronous.

Every DB-backed domain model should inherit from `Entity()` or `IdEntity`, which gives it `_id`, `_created_date`, and `_updated_date`.

```python
from dataclasses import dataclass

from models.base.entity import Entity


@dataclass
class Project(Entity()):
    name: str
```

DAOs are the service-facing persistence layer. The generic `EntityDAO[TEntity]` wraps a backend-neutral `Repository[TEntity]` and owns shared entity lifecycle behavior such as ensuring IDs and updating timestamps before persistence.

```python
from persistence.daos.entity_dao import EntityDAO
from persistence.repository import Repository


class ProjectDAO(EntityDAO[Project]):
    def __init__(self, repository: Repository[Project]):
        super().__init__(repository)

    async def get_by_name(self, name: str) -> Project | None:
        return await self.find_one({"name": name})
```

Concrete repository implementations live under `server/db/repository` and own driver-specific connection details. API, service, and DAO code should not use `pymongo`, `psycopg`, `aiosqlite`, collection, cursor, or connection types directly.

The repository contract is async:

```python
entity = await repo.create(entity)
entity = await repo.get_by_id("entity-id")
entity = await repo.find_one({"email": "user@example.com"})
entities = await repo.enumerate(limit=100, offset=0)
entity = await repo.update("entity-id", {"field": "value"})
deleted = await repo.delete("entity-id")
await repo.close()
```

Repository objects can still be constructed synchronously. Async is used where I/O actually occurs, so constructors and serializers do not need to become awaitable simply because they participate in the persistence stack.

## FastAPI dependency injection

Prefer injecting services into endpoints. Services depend on DAOs, and DAOs depend on repositories. Keep `Depends(...)` visible at the point where each dependency is requested instead of hiding it behind type aliases.

Dependency providers that only construct objects can remain ordinary synchronous functions:

```python
from typing import Annotated

from fastapi import Depends

from persistence.dependencies import repository_dependency
from persistence.pserialize_entity_serializer import PSerializeEntitySerializer
from persistence.repository import Repository

get_project_repository = repository_dependency(
    resource_name="projects",
    serializer=PSerializeEntitySerializer(Project),
)


def get_project_dao(
    project_repository: Annotated[Repository[Project], Depends(get_project_repository)],
) -> ProjectDAO:
    return ProjectDAO(project_repository)
```

Then wire the service explicitly as well:

```python
def get_project_service(
    project_dao: Annotated[ProjectDAO, Depends(get_project_dao)],
) -> ProjectService:
    return ProjectService(project_dao)
```

DB-backed endpoint functions should be async and await service operations:

```python
@router.get("/{project_id}")
async def get_project(
    project_id: str,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> Project:
    return await project_service.get_by_id(project_id)
```

The template includes ready-made `UserDAO`, `SessionDAO`, and service dependency providers for the starter user/session routes.

## Route authentication and permissions

Use the existing route annotations. They attach metadata only; the custom router converts that metadata into FastAPI dependencies during route registration while preserving async endpoint execution.

Authentication-only route:

```python
from api.decorators.authenticated import authenticated


@router.get("/me")
@authenticated()
async def get_me():
    ...
```

Permission-protected route:

```python
from api.decorators.check_permissions import check_permission


@router.get("/{project_id}")
@check_permission("read/projects/{project_id}")
async def get_project(project_id: str):
    ...
```

`check_permission(...)` implies authentication. Permission templates can reference route path parameters, which are resolved before the async `AuthorizationService` access check is awaited.

## Database backend selection

Select the backend with environment variables:

```bash
APP_DB_BACKEND=mongo
APP_DB_URI=mongodb://localhost:27017
APP_DB_NAME=my_app
```

Mongo uses PyMongo's native async client.

Or use Postgres:

```bash
APP_DB_BACKEND=postgres
APP_DB_URI=postgresql://postgres:postgres@localhost:5432/my_app
APP_DB_NAME=my_app
```

Postgres uses psycopg's async connection API.

Or use SQLite:

```bash
APP_DB_BACKEND=sqlite
APP_DB_URI=sqlite:///my_app.db
APP_DB_NAME=my_app
```

SQLite uses `aiosqlite` so SQLite operations do not block the FastAPI event loop.

The repository interface intentionally exposes only application entities and primitive Python values. Database-driver types stay behind the repository boundary.

## Setup this template repo locally

Install dependencies from the repository root:

```bash
pip install -r requirements.txt
```

Run the development server:

```bash
uvicorn server.main:app --reload
```

## Suggested project structure

```text
.
├── server/
│   ├── api/
│   ├── auth/
│   ├── db/
│   │   ├── daos/
│   │   ├── repository/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── pserialize_entity_serializer.py
│   ├── models/
│   ├── service/
│   ├── users/
│   └── main.py
├── server_template/
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## How to use this template manually

1. Clone or copy the repository.
2. Rename the application/package to match the new service.
3. Pick `APP_DB_BACKEND=mongo`, `postgres`, or `sqlite`.
4. Add domain models that inherit from `Entity()`.
5. Add domain DAOs that inherit from `EntityDAO[TEntity]`.
6. Make persistence-facing DAO methods async and await repository operations.
7. Add services that depend on DAOs, not concrete DB drivers, and await I/O-performing DAO methods.
8. Add async DB-backed endpoints that depend on services through FastAPI `Depends(...)` providers.
9. Add `@authenticated()` or `@check_permission(...)` where route access must be restricted.
10. Add tests before using it as a production service.

## Status

Template / starter project.

## License

No license has been selected yet.

## Local virtual environment (venv) setup

If you want to work in an isolated virtual environment, create a `.venv` in the repository root and install dependencies:

PowerShell:

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Command Prompt (cmd.exe):

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

If `python` is not available on your PATH, install Python 3.14+ from https://www.python.org/ or use the Windows `py` launcher if present:

```powershell
py -3.14 -m venv .venv
. .venv\Scripts\Activate.ps1
.venv\Scripts\pip.exe install -r requirements.txt
```

If you prefer not to activate the environment, you can run the venv Python/pip directly from `.venv\Scripts/`.
### Run the test suite

Install the test dependencies from the repository root:

```powershell
python -m pip install -e ".[test]"
```

Then run the tests:

```powershell
python -m pytest tests -q
```

You can also limit the run to a specific test file:

```powershell
python -m pytest tests/api/test_users_api.py
```

The project is configured so pytest uses the repository's `tests` folder and adds the `server` package to `PYTHONPATH` automatically.
### Type and lint checks

Install the development quality tools with the project and run the same checks used in CI:

```powershell
python -m pip install -e ".[quality]"
python -m mypy
python -m ruff check server server_template tests test-scafold --fix
python -m pytest test-scafold/tests tests  
$env:APP_DB_BACKEND = "sqlite"
$env:APP_DB_URI = "sqlite:///local-api-test.db"
$env:APP_DB_NAME = "local_api_test"
```
