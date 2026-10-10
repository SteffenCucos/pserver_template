
import pytest

from typing_extensions import cast

from server.persistence.dependencies import DatabaseSettings
from server.persistence.repository.factory import DatabaseBackend, create_repository
from server.persistence.repository.mongo import MongoRepository
from server.persistence.repository.postgres import PostgresRepository
from server.persistence.repository.sqlite import SQLiteRepository


@pytest.mark.parametrize(
    "settings, expected_type",
    [
        (
            DatabaseSettings(
                backend=DatabaseBackend.MONGO,
                uri="mongodb://localhost:27017",
                database="test_db",
            ),
            MongoRepository
        ),
        (
            DatabaseSettings(
                backend=DatabaseBackend.POSTGRES,
                uri="postgresql://user:password@localhost/test_db",
                database="test_db",
            ),
            PostgresRepository,
        ),
        (
            DatabaseSettings(
                backend=DatabaseBackend.SQLITE,
                uri="sqlite:///test_db.sqlite",
                database="test_db",
            ),
            SQLiteRepository,
        ),
        (
            DatabaseSettings(
                backend=cast(DatabaseBackend, "UNKOWN"),
                uri="unkown:///:memory:",
                database="test_db",
            ),
            Exception,
        )
    ],
)
def test_create_repository(settings: DatabaseSettings, expected_type: type):
    if expected_type is Exception:
        with pytest.raises(ValueError):
            create_repository(
                settings=settings,
                resource_name="test_collection",
                serializer=None,  # type: ignore
            )
    else:
        repository = create_repository(
            settings=settings,
            resource_name="test_collection",
            serializer=None,  # type: ignore
        )
        assert isinstance(repository, expected_type)
