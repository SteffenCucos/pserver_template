
"""Database abstraction layer."""

from .config import DatabaseBackend, DatabaseSettings
from .daos.entity_dao import EntityDAO
from .repository import EntitySerializer, MappingSerializer, Repository


__all__ = [
    "DatabaseBackend",
    "DatabaseSettings",
    "EntityDAO",
    "EntitySerializer",
    "MappingSerializer",
    "Repository",
]
