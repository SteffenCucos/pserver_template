
from __future__ import annotations

import importlib
import os
import subprocess
import sys
import time

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[4]
configured_app_root = os.environ.get("TEST_SCAFOLD_APP_ROOT")
APP_ROOT = Path(configured_app_root).resolve() if configured_app_root else PROJECT_ROOT
SERVER_ROOT = APP_ROOT / "server"

IN_MEMORY_URIS = {"mongo": "memory://", "sqlite": "sqlite:///:memory:"}
# CI runs one backend per job by setting APP_DB_BACKEND (and optionally APP_DB_URI).
# Without it, every test runs against every backend.
BACKENDS = [os.environ["APP_DB_BACKEND"]] if "APP_DB_BACKEND" in os.environ else ["mongo", "sqlite", "postgres"]
CONFIGURED_URI = os.environ.get("APP_DB_URI") if "APP_DB_BACKEND" in os.environ else None
POSTGRES_STARTUP_TIMEOUT_SECONDS = 60


def _clear_scaffold_modules() -> None:
    prefixes = ("api", "auth", "config", "persistence", "main", "models", "service", "users")
    for module_name in list(sys.modules):
        if any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in prefixes):
            sys.modules.pop(module_name, None)


def _wait_for_postgres(uri: str) -> None:
    import psycopg

    # Connect over TCP rather than using pg_isready: the image's init server only listens on a
    # unix socket, so TCP succeeds once the real server is up.
    deadline = time.monotonic() + POSTGRES_STARTUP_TIMEOUT_SECONDS
    while True:
        try:
            with psycopg.connect(uri, connect_timeout=1) as connection:
                connection.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture(scope="session")
def postgres_uri() -> Iterator[str]:
    """
    Run a throwaway Postgres container for the session, on a random port so it never collides
    with a local Postgres.
    """
    container = f"api-tests-postgres-{uuid4().hex[:8]}"
    try:
        subprocess.run(
            [
                "docker", "run", "--detach", "--rm",
                "--name", container,
                "--env", "POSTGRES_PASSWORD=postgres",
                "--publish", "127.0.0.1::5432",
                "postgres:16",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        details = e.stderr.strip() if isinstance(e, subprocess.CalledProcessError) else str(e)
        pytest.fail(
            f"Postgres API tests need Docker running: {details}\n"
            "Start Docker, or run a single backend with APP_DB_BACKEND=mongo|sqlite."
        )

    try:
        mapping = subprocess.run(
            ["docker", "port", container, "5432/tcp"], check=True, capture_output=True, text=True
        ).stdout
        port = mapping.splitlines()[0].rsplit(":", 1)[1]
        uri = f"postgresql://postgres:postgres@127.0.0.1:{port}/postgres"
        _wait_for_postgres(uri)
        yield uri
    finally:
        subprocess.run(["docker", "rm", "--force", container], capture_output=True)


@pytest.fixture(scope="session")
def mongo_uri() -> Iterator[str]:
    """
    Run one in-memory mongod for the session. The app starts its own for memory:// URIs, but it
    caches that server in a module the client fixture reloads for every test, so each test would
    start another mongod and they'd pile up until one fails to bind its port.
    """
    from pymongo_inmemory import MongoClient

    server = MongoClient()
    try:
        address = server.address
        assert address is not None, "in-memory mongod did not report an address"
        host, port = address
        yield f"mongodb://{host}:{port}"
    finally:
        server.close()


@pytest.fixture(params=BACKENDS)
def client(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    assert APP_ROOT.exists(), f"application root does not exist: {APP_ROOT}"
    assert SERVER_ROOT.exists(), f"server package does not exist: {SERVER_ROOT}"

    backend: str = request.param
    uri = CONFIGURED_URI or IN_MEMORY_URIS.get(backend)
    if uri == IN_MEMORY_URIS["mongo"]:
        uri = request.getfixturevalue("mongo_uri")
    elif uri is None:
        uri = request.getfixturevalue("postgres_uri")

    monkeypatch.setenv("APP_DB_NAME", f"api_tests_{uuid4().hex}")
    monkeypatch.setenv("APP_DB_BACKEND", backend)
    monkeypatch.setenv("APP_DB_URI", uri)
    _clear_scaffold_modules()

    sys.path.insert(0, str(APP_ROOT))
    sys.path.insert(0, str(SERVER_ROOT))
    main = importlib.import_module("main")
    with TestClient(main.app) as test_client:
        yield test_client
