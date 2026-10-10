
import asyncio

from unittest.mock import create_autospec

from server.auth.rbac.daos.user_role_dao import UserRoleDAO
from server.auth.rbac.models import UserRole
from server.models.base.id import Id
from server.persistence.repository import Repository


def test_list_for_user_filters_enumerated_user_roles() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = UserRoleDAO(repository)
        user_id = Id("user-1")
        matching_role = UserRole(user_id=user_id, role_id=Id("admin"))
        other_role = UserRole(user_id=Id("user-2"), role_id=Id("admin"))
        repository.enumerate.return_value = [matching_role, other_role]

        assert await dao.list_for_user(Id("user-1")) == [matching_role]

        repository.enumerate.assert_awaited_once_with(limit=-1, offset=0)

    asyncio.run(run_test())


def test_list_for_role_filters_enumerated_user_roles() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = UserRoleDAO(repository)
        admin_id = Id("admin")
        admin_user = UserRole(user_id=Id("user-1"), role_id=admin_id)
        reader_user = UserRole(user_id=Id("user-2"), role_id=Id("reader"))
        repository.enumerate.return_value = [admin_user, reader_user]

        assert await dao.list_for_role(Id("admin")) == [admin_user]

        repository.enumerate.assert_awaited_once_with(limit=-1, offset=0)

    asyncio.run(run_test())
