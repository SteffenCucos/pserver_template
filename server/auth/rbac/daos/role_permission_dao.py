
from __future__ import annotations

from persistence.daos.entity_dao import EntityDAO
from persistence.repository import Repository

from auth.rbac import RolePermission
from models.base.id import Id


class RolePermissionDAO(EntityDAO[RolePermission]):
    def __init__(self, repository: Repository[RolePermission]) -> None:
        super().__init__(repository)

    async def list_for_role(self, role_id: Id) -> list[RolePermission]:
        return [
            item for item in await self.enumerate() if str(item.role_id) == str(role_id)
        ]

    async def list_for_perm(self, permission_id: Id) -> list[RolePermission]:
        return [
            item
            for item in await self.enumerate()
            if str(item.permission_id) == str(permission_id)
        ]
