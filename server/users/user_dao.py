
from __future__ import annotations

from persistence.daos.entity_dao import EntityDAO
from persistence.repository import Repository

from models.base.id import Id
from users.user import User


class UserDAO(EntityDAO[User]):
    def __init__(self, repository: Repository[User]) -> None:
        super().__init__(repository)

    async def get_by_name(self, user_name: str) -> User | None:
        return await self.find_one({"user_name": user_name})

    async def get_by_email(self, email: str) -> User | None:
        return await self.find_one({"email": email})

    async def update_password_hash(self, user_id: Id, password_hash: str) -> User | None:
        return await self.update(user_id, {"password_hash": password_hash})
