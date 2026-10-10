
import asyncio

from unittest.mock import create_autospec

from server.auth.authorization_service import AuthorizationService
from server.auth.rbac import Permission, PermissionTree, RolePermission, TreeStore, UserRole
from server.auth.rbac.authorization_tree_service import AuthorizationTreeService
from server.auth.rbac.daos import RolePermissionDAO, UserRoleDAO
from server.auth.rbac.permission_service import PermissionService
from server.auth.rbac.role_service import RoleService
from server.models.base.id import Id


def _mock_daos():
    return (
        create_autospec(UserRoleDAO, instance=True),
        create_autospec(RolePermissionDAO, instance=True),
        create_autospec(PermissionService, instance=True),
    )


def test_role_store_no_reload_on_no_match():
    async def run_test():
        user_id = Id("u1")
        role_id = Id("r1")
        role_tree = PermissionTree()
        role_tree.add("read/users/*")

        store = TreeStore()
        store.role_ids_by_user_id[user_id] = [role_id]
        store.role_tree_by_role_id[role_id] = role_tree

        user_role_dao, role_permission_dao, permission_service = _mock_daos()
        tree_service = AuthorizationTreeService(
            user_role_dao,
            role_permission_dao,
            permission_service,
            store,
        )
        service = AuthorizationService(
            role_permission_dao,
            user_role_dao,
            create_autospec(RoleService, instance=True),
            permission_service,
            tree_service,
        )

        assert not await service.user_has_access(user_id, "delete/users/123")
        user_role_dao.list_for_user.assert_not_awaited()
        role_permission_dao.list_for_role.assert_not_awaited()
        permission_service.get_permission.assert_not_awaited()

    asyncio.run(run_test())


def test_role_store_loads_once():
    async def run_test():
        user_id = Id("u1")
        role_id = Id("r1")
        permission = Permission("read/users/*")

        user_role_dao, role_permission_dao, permission_service = _mock_daos()
        user_role_dao.list_for_user.return_value = [
            UserRole(user_id=user_id, role_id=role_id),
        ]
        role_permission_dao.list_for_role.return_value = [
            RolePermission(role_id=role_id, permission_id=permission.id),
        ]
        permission_service.get_permission.return_value = permission

        tree_service = AuthorizationTreeService(
            user_role_dao,
            role_permission_dao,
            permission_service,
            TreeStore(),
        )
        service = AuthorizationService(
            role_permission_dao,
            user_role_dao,
            create_autospec(RoleService, instance=True),
            permission_service,
            tree_service,
        )

        assert await service.user_has_access(user_id, "read/users/123")
        assert await service.user_has_access(user_id, "read/users/456")

        user_role_dao.list_for_user.assert_awaited_once_with(user_id)
        role_permission_dao.list_for_role.assert_awaited_once_with(role_id)
        permission_service.get_permission.assert_awaited_once_with(permission.id)

    asyncio.run(run_test())
