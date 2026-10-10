
from models.base.id import Id

from .permission_tree import PermissionTree


class TreeStore:
    def __init__(self) -> None:
        self.role_ids_by_user_id: dict[Id, list[Id]] = {}
        self.role_tree_by_role_id: dict[Id, PermissionTree] = {}

    def invalidate_user(self, user_id: Id) -> None:
        self.role_ids_by_user_id.pop(user_id, None)

    def invalidate_role(self, role_id: Id) -> None:
        self.role_tree_by_role_id.pop(role_id, None)

    def clear(self) -> None:
        self.role_ids_by_user_id.clear()
        self.role_tree_by_role_id.clear()
