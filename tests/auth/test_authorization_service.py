
import asyncio

from unittest.mock import create_autospec

from server.auth.authorization_service import AuthorizationService
from server.auth.rbac import Permission, RolePermission, TreeStore, UserRole
from server.auth.rbac.authorization_tree_service import AuthorizationTreeService
from server.auth.rbac.daos import RolePermissionDAO, UserRoleDAO
from server.auth.rbac.permission_service import PermissionService
from server.auth.rbac.role_service import RoleService
from server.models.base.id import Id


def test_user_has_access_through_role_permission():
    async def run_test():
        user_id = Id("user-1")
        role_id = Id("admin")
        perm = Permission("read/users/.+")

        user_role_dao = create_autospec(UserRoleDAO, instance=True)
        role_permission_dao = create_autospec(RolePermissionDAO, instance=True)
        permission_service = create_autospec(PermissionService, instance=True)

        user_role_dao.list_for_user.return_value = [
            UserRole(user_id=user_id, role_id=role_id),
        ]
        role_permission_dao.list_for_role.return_value = [
            RolePermission(role_id=role_id, permission_id=perm.id),
        ]
        permission_service.get_permission.return_value = perm

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
        assert not await service.user_has_access(user_id, "delete/users/123")

        user_role_dao.list_for_user.assert_awaited_once_with(user_id)
        role_permission_dao.list_for_role.assert_awaited_once_with(role_id)
        permission_service.get_permission.assert_awaited_once_with(perm.id)

    asyncio.run(run_test())
