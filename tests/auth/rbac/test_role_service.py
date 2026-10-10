
import asyncio

from unittest.mock import create_autospec

from server.auth.rbac.daos.role_dao import RoleDAO
from server.auth.rbac.models import Role
from server.auth.rbac.role_service import RoleService
from server.models.base.id import Id


def make_role(name: str = "admin", description: str = "Administrator") -> Role:
    return Role(name=name, description=description)


def test_get_delete_and_enumerate_roles_delegate_to_dao() -> None:
    async def run_test() -> None:
        role_dao = create_autospec(RoleDAO, instance=True)
        service = RoleService(role_dao)
        role = make_role()
        role_id = Id("admin")
        role_dao.get_by_id.return_value = role
        role_dao.delete.return_value = True
        role_dao.enumerate.return_value = [role]

        assert await service.get_role(role_id) is role
        assert await service.delete_role(role_id) is True
        assert await service.enumerate_rolls() == [role]

        role_dao.get_by_id.assert_awaited_once_with(role_id)
        role_dao.delete.assert_awaited_once_with(role_id)
        role_dao.enumerate.assert_awaited_once_with()

    asyncio.run(run_test())


def test_create_or_update_role_creates_a_new_role_when_name_is_available() -> None:
    async def run_test() -> None:
        role_dao = create_autospec(RoleDAO, instance=True)
        service = RoleService(role_dao)
        created_role = make_role()
        role_dao.get_by_name.return_value = None
        role_dao.create.return_value = created_role

        assert await service.create_or_update_role("admin", "Administrator") is created_role

        role_dao.get_by_name.assert_awaited_once_with("admin")
        role_dao.create.assert_awaited_once()
        role_to_create = role_dao.create.await_args.args[0]
        assert role_to_create.name == "admin"
        assert role_to_create.description == "Administrator"
        role_dao.update_entity.assert_not_awaited()

    asyncio.run(run_test())


def test_create_or_update_role_returns_existing_role_without_a_write_when_unchanged() -> None:
    async def run_test() -> None:
        role_dao = create_autospec(RoleDAO, instance=True)
        service = RoleService(role_dao)
        role = make_role()
        role_dao.get_by_name.return_value = role

        assert await service.create_or_update_role("admin", "Administrator") is role

        role_dao.update_entity.assert_not_awaited()
        role_dao.create.assert_not_awaited()

    asyncio.run(run_test())


def test_create_or_update_role_updates_existing_role_description() -> None:
    async def run_test() -> None:
        role_dao = create_autospec(RoleDAO, instance=True)
        service = RoleService(role_dao)
        role = make_role(description="Old description")
        role_dao.get_by_name.return_value = role

        assert await service.create_or_update_role("admin", "New description") is role

        assert role.description == "New description"
        role_dao.update_entity.assert_awaited_once_with(role)
        role_dao.create.assert_not_awaited()

    asyncio.run(run_test())
