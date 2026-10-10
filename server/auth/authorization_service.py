
from auth.rbac.authorization_tree_service import AuthorizationTreeService
from auth.rbac.daos import RolePermissionDAO
from auth.rbac.daos.user_role_dao import UserRoleDAO
from auth.rbac.models import Permission, Role, RolePermission, UserRole
from auth.rbac.permission_service import PermissionService
from auth.rbac.role_service import RoleService
from models.base.id import Id


class AuthorizationService:
    def __init__(
        self,
        role_permission_dao: RolePermissionDAO,
        user_role_dao: UserRoleDAO,
        role_service: RoleService,
        permission_service: PermissionService,
        authorization_tree_service: AuthorizationTreeService
    ) -> None:
        self.role_permission_dao = role_permission_dao
        self.user_role_dao = user_role_dao
        self.role_service = role_service
        self.permission_service = permission_service
        self.authorization_tree_service = authorization_tree_service

    async def user_has_access(self, user_id: Id, permission_string: str) -> bool:
        return await self.authorization_tree_service.user_has_access(user_id, permission_string)

    async def create_role(self, name: str, description: str) -> Role:
        return await self.role_service.create_or_update_role(name, description)

    async def create_permission(self, description: str, key: str) -> Permission:
        return await self.permission_service.create_or_update_permission(description, key)

    async def create_role_permission(self, role_id: Id, permission_id: Id) -> RolePermission:
        return await self.role_permission_dao.create(RolePermission(role_id, permission_id))

    async def create_user_role(self, user_id: Id, role_id: Id) -> UserRole:
        user_role = await self.user_role_dao.create(UserRole(user_id, role_id))
        # Invalidate the cache for the user's roles in the authorization tree service
        self.authorization_tree_service.add_user_role(user_id, role_id)
        return user_role
