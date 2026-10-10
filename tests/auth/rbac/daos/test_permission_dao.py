
import asyncio

from unittest.mock import create_autospec

from server.auth.rbac.daos.permission_dao import PermissionDAO
from server.auth.rbac.models import Permission
from server.persistence.repository import Repository


def test_get_by_key_queries_repository_with_permission_key() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = PermissionDAO(repository)
        permission = Permission(key="read/users", description="Read users")
        repository.find_one.return_value = permission

        assert await dao.get_by_key("read/users") is permission

        repository.find_one.assert_awaited_once_with({"key": "read/users"})

    asyncio.run(run_test())
