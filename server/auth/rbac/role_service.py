
from auth.rbac.daos.role_dao import RoleDAO
from auth.rbac.models import Role
from models.base.id import Id


class RoleService:
    def __init__(self, role_dao: RoleDAO):
        self.role_dao = role_dao

    async def get_role(self, role_id: Id) -> Role | None:
        return await self.role_dao.get_by_id(role_id)

    async def create_or_update_role(self, name: str, description: str) -> Role:
        exists = await self.role_dao.get_by_name(name)
        if exists:
            if exists.description != description:
                exists.description = description
                await self.role_dao.update_entity(exists)

            return exists

        role = await self.role_dao.create(Role(
            name=name,
            description=description,
        ))
        return role

    async def delete_role(self, id: Id) -> bool:
        return await self.role_dao.delete(id)

    async def enumerate_rolls(self) -> list[Role]:
        return await self.role_dao.enumerate()
