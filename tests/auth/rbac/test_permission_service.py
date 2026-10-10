
import asyncio

from unittest.mock import create_autospec

from server.auth.rbac.daos.permission_dao import PermissionDAO
from server.auth.rbac.models import Permission
from server.auth.rbac.permission_service import PermissionService
from server.models.base.id import Id


def make_permission(key: str = "read/users", description: str = "Read users") -> Permission:
    return Permission(key=key, description=description)


def test_get_and_delete_permission_delegate_to_dao() -> None:
    async def run_test() -> None:
        permission_dao = create_autospec(PermissionDAO, instance=True)
        service = PermissionService(permission_dao)
        permission = make_permission()
        permission_id = Id("permission-id")
        permission_dao.get_by_id.return_value = permission
        permission_dao.delete.return_value = True

        assert await service.get_permission(permission_id) is permission
        assert await service.delete_permission(permission_id) is True

        permission_dao.get_by_id.assert_awaited_once_with(permission_id)
        permission_dao.delete.assert_awaited_once_with(permission_id)

    asyncio.run(run_test())


def test_create_or_update_permission_creates_new_permission_when_key_is_available() -> None:
    async def run_test() -> None:
        permission_dao = create_autospec(PermissionDAO, instance=True)
        service = PermissionService(permission_dao)
        created_permission = make_permission()
        permission_dao.get_by_key.return_value = None
        permission_dao.create.return_value = created_permission

        assert await service.create_or_update_permission("Read users", "read/users") is created_permission

        permission_dao.get_by_key.assert_awaited_once_with("read/users")
        permission_dao.create.assert_awaited_once()
        permission_to_create = permission_dao.create.await_args.args[0]
        assert permission_to_create.key == "read/users"
        assert permission_to_create.description == "Read users"
        permission_dao.update_entity.assert_not_awaited()

    asyncio.run(run_test())


def test_create_or_update_permission_returns_existing_permission_without_a_write_when_unchanged() -> None:
    async def run_test() -> None:
        permission_dao = create_autospec(PermissionDAO, instance=True)
        service = PermissionService(permission_dao)
        permission = make_permission()
        permission_dao.get_by_key.return_value = permission

        assert await service.create_or_update_permission("Read users", "read/users") is permission

        permission_dao.update_entity.assert_not_awaited()
        permission_dao.create.assert_not_awaited()

    asyncio.run(run_test())


def test_create_or_update_permission_updates_existing_permission_description() -> None:
    async def run_test() -> None:
        permission_dao = create_autospec(PermissionDAO, instance=True)
        service = PermissionService(permission_dao)
        permission = make_permission(description="Old description")
        permission_dao.get_by_key.return_value = permission

        assert await service.create_or_update_permission("New description", "read/users") is permission

        assert permission.description == "New description"
        permission_dao.update_entity.assert_awaited_once_with(permission)
        permission_dao.create.assert_not_awaited()

    asyncio.run(run_test())
