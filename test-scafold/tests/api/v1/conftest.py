
from __future__ import annotations

import importlib
import os
import sys

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[4]
configured_app_root = os.environ.get("TEST_SCAFOLD_APP_ROOT")
APP_ROOT = Path(configured_app_root).resolve() if configured_app_root else PROJECT_ROOT
SERVER_ROOT = APP_ROOT / "server"


def _clear_scaffold_modules() -> None:
    prefixes = ("api", "auth", "config", "persistence", "main", "models", "service", "users")
    for module_name in list(sys.modules):
        if any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in prefixes):
            sys.modules.pop(module_name, None)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    assert APP_ROOT.exists(), f"application root does not exist: {APP_ROOT}"
    assert SERVER_ROOT.exists(), f"server package does not exist: {SERVER_ROOT}"

    monkeypatch.setenv("APP_DB_NAME", f"api_tests_{uuid4().hex}")
    if "APP_DB_BACKEND" not in os.environ:
        monkeypatch.setenv("APP_DB_BACKEND", "sqlite")
    if "APP_DB_URI" not in os.environ:
        monkeypatch.setenv("APP_DB_URI", "sqlite:///:memory:")
    _clear_scaffold_modules()

    sys.path.insert(0, str(APP_ROOT))
    sys.path.insert(0, str(SERVER_ROOT))
    main = importlib.import_module("main")
    with TestClient(main.app) as test_client:
        yield test_client
