
from auth.rbac.daos import RolePermissionDAO, UserRoleDAO
from auth.rbac.permission_service import PermissionService
from auth.rbac.permission_tree import PermissionTree
from auth.rbac.tree_store import TreeStore
from models.base.id import Id


_STORE = TreeStore()
_TREE_CLASS = PermissionTree


class AuthorizationTreeService:
    '''
    Wrapper/Cache overtop of the authn concepts that reperesents permissions and roles as a tree structure. 
    This is used to determine if a user has access to a given permission key.
    '''
    def __init__(
        self,
        user_role_dao: UserRoleDAO,
        role_permission_dao: RolePermissionDAO,
        permission_service: PermissionService,
        tree_store: TreeStore | None = None,
    ) -> None:
        self.user_role_dao = user_role_dao
        self.role_permission_dao = role_permission_dao
        self.permission_service = permission_service
        self.tree_store = tree_store or _STORE

    async def user_has_access(self, user_id: Id, required: str) -> bool:
        for role_id in await self._role_ids_for_user(user_id):
            role_tree = await self._tree_for_role(role_id)
            if role_tree.allows(required):
                return True
        return False

    def add_user_role(self, user_id: Id, role_id: Id) -> None:
        # Invalidate the cache for the user's roles in the tree store
        self.tree_store.invalidate_user(user_id)
        # Invalidate the cache for the role's permission tree in the tree store
        self.tree_store.invalidate_role(role_id)

    async def _role_ids_for_user(self, user_id: Id) -> list[Id]:
        if user_id not in self.tree_store.role_ids_by_user_id:
            self.tree_store.role_ids_by_user_id[user_id] = [
                user_role.role_id
                for user_role in await self.user_role_dao.list_for_user(user_id)
            ]
        return self.tree_store.role_ids_by_user_id[user_id]

    async def _tree_for_role(self, role_id: Id) -> PermissionTree:
        if role_id not in self.tree_store.role_tree_by_role_id:
            self.tree_store.role_tree_by_role_id[role_id] = await self._build_tree_for_role(
                role_id
            )
        return self.tree_store.role_tree_by_role_id[role_id]

    async def _build_tree_for_role(self, role_id: Id) -> PermissionTree:
        role_tree = _TREE_CLASS()
        for role_perm in await self.role_permission_dao.list_for_role(role_id):
            perm = await self.permission_service.get_permission(role_perm.permission_id)
            if perm:
                role_tree.add(perm.key)
        return role_tree
