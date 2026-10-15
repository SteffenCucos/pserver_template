
from __future__ import annotations

from persistence.daos.entity_dao import EntityDAO
from persistence.repository import Repository

from auth.rbac import UserRole
from models.base.id import Id


class UserRoleDAO(EntityDAO[UserRole]):
    def __init__(self, repository: Repository[UserRole]) -> None:
        super().__init__(repository)

    async def list_for_user(self, user_id: Id) -> list[UserRole]:
        return [
            item for item in await self.enumerate() if str(item.user_id) == str(user_id)
        ]

    async def list_for_role(self, role_id: Id) -> list[UserRole]:
        return [
            item for item in await self.enumerate() if str(item.role_id) == str(role_id)
        ]
