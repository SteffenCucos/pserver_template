
"""Database backend configuration helpers."""

from __future__ import annotations

import os

from dataclasses import dataclass
from enum import Enum


class DatabaseBackend(str, Enum):
    """Supported database backend families."""

    MONGO = "mongo"
    POSTGRES = "postgres"
    SQLITE = "sqlite"

_db_settings: DatabaseSettings | None = None

@dataclass(frozen=True)
class DatabaseSettings:
    """Backend-neutral database settings.

    Keep this object free of driver-specific types so it can be passed through
    application code without coupling the app layer to Mongo or SQL libraries.
    """

    backend: DatabaseBackend
    uri: str
    database: str

    @classmethod
    def from_env(cls, prefix: str = "APP_DB") -> "DatabaseSettings":
        """Build settings from environment variables.

        Supported variables for the default prefix are:
        - APP_DB_BACKEND: mongo | postgres | sqlite
        - APP_DB_URI: database connection URI
        - APP_DB_NAME: logical database name
        """
        global _db_settings
        if _db_settings:
            return _db_settings
        backend = DatabaseBackend(os.getenv(f"{prefix}_BACKEND", DatabaseBackend.MONGO.value))
        database = os.getenv(f"{prefix}_NAME", "app")
        uri = os.getenv(f"{prefix}_URI") or default_uri_for_backend(backend, database)
        _db_settings =  cls(backend=backend, uri=uri, database=database)
        return _db_settings


def default_uri_for_backend(backend: DatabaseBackend, database: str) -> str:
    """Return a local-development URI for the selected backend."""
    if backend == DatabaseBackend.MONGO:
        return "mongodb://localhost:27017"
    if backend == DatabaseBackend.POSTGRES:
        return f"postgresql://postgres:postgres@localhost:5432/{database}"
    if backend == DatabaseBackend.SQLITE:
        return f"sqlite:///{database}.db"
    raise ValueError(f"unsupported database backend: {backend}")
