
from __future__ import annotations

from persistence.daos.entity_dao import EntityDAO
from persistence.repository import Repository

from auth.rbac import Permission


class PermissionDAO(EntityDAO[Permission]):
    def __init__(self, repository: Repository[Permission]) -> None:
        super().__init__(repository)

    async def get_by_key(self, key: str) -> Permission | None:
        return await self.find_one({"key": key})
