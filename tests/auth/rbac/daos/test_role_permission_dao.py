
import asyncio

from unittest.mock import create_autospec

from server.auth.rbac.daos.role_permission_dao import RolePermissionDAO
from server.auth.rbac.models import RolePermission
from server.models.base.id import Id
from server.persistence.repository import Repository


def test_list_for_role_filters_enumerated_role_permissions() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = RolePermissionDAO(repository)
        admin_id = Id("admin")
        admin_permission = RolePermission(role_id=admin_id, permission_id=Id("read/users"))
        reader_permission = RolePermission(role_id=Id("reader"), permission_id=Id("read/users"))
        repository.enumerate.return_value = [admin_permission, reader_permission]

        assert await dao.list_for_role(Id("admin")) == [admin_permission]

        repository.enumerate.assert_awaited_once_with(limit=-1, offset=0)

    asyncio.run(run_test())


def test_list_for_perm_filters_enumerated_role_permissions() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = RolePermissionDAO(repository)
        read_permission_id = Id("read/users")
        read_permission = RolePermission(role_id=Id("admin"), permission_id=read_permission_id)
        write_permission = RolePermission(role_id=Id("admin"), permission_id=Id("write/users"))
        repository.enumerate.return_value = [read_permission, write_permission]

        assert await dao.list_for_perm(Id("read/users")) == [read_permission]

        repository.enumerate.assert_awaited_once_with(limit=-1, offset=0)

    asyncio.run(run_test())
