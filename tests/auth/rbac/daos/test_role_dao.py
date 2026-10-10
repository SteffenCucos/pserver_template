
import asyncio

from unittest.mock import create_autospec

from server.auth.rbac.daos.role_dao import RoleDAO
from server.auth.rbac.models import Role
from server.persistence.repository import Repository


def test_get_by_name_queries_repository_with_role_name() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = RoleDAO(repository)
        role = Role(name="admin", description="Administrator")
        repository.find_one.return_value = role

        assert await dao.get_by_name("admin") is role

        repository.find_one.assert_awaited_once_with({"name": "admin"})

    asyncio.run(run_test())
