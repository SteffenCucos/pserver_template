
from auth.rbac.daos.permission_dao import PermissionDAO
from auth.rbac.models import Permission
from models.base.id import Id


class PermissionService:
    def __init__(self, permission_dao: PermissionDAO):
        self.permission_dao = permission_dao

    async def create_or_update_permission(self, description: str, key: str) -> Permission:
        exists = await self.permission_dao.get_by_key(key)
        if exists:
            if exists.description != description:
                exists.description = description
                await self.permission_dao.update_entity(exists)

            return exists

        permission = await self.permission_dao.create(Permission(
            description=description,
            key=key,
        ))
        return permission

    async def get_permission(self, id: Id) -> Permission | None:
        return await self.permission_dao.get_by_id(id)

    async def delete_permission(self, id: Id) -> bool:
        return await self.permission_dao.delete(id)
