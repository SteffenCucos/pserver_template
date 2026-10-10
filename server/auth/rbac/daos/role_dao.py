
from __future__ import annotations

from persistence.daos.entity_dao import EntityDAO
from persistence.repository import Repository

from auth.rbac import Role


class RoleDAO(EntityDAO[Role]):
    def __init__(self, repository: Repository[Role]) -> None:
        super().__init__(repository)

    async def get_by_name(self, name: str) -> Role | None:
        return await self.find_one({"name": name})
