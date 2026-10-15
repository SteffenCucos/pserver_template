
from __future__ import annotations

from persistence.daos.entity_dao import EntityDAO
from persistence.repository import Repository

from auth.session.session import Session
from models.base.id import Id


class SessionDAO(EntityDAO[Session]):
    def __init__(self, repository: Repository[Session]) -> None:
        super().__init__(repository)

    async def list_for_user(self, user_id: Id) -> list[Session]:
        return [
            session
            for session in await self.enumerate()
            if str(session.user_id) == str(user_id)
        ]
