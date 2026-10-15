
import logging

from auth.session.session import Session
from models.base.id import Id
from users.user import User

from .session_dao import SessionDAO


logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, dao: SessionDAO) -> None:
        self.dao = dao

    async def create_session(self, user: User) -> Session:
        session = Session(user.id)
        return await self.dao.create(session)

    async def get_session(self, session_id: Id) -> Session | None:
        return await self.dao.get_by_id(session_id)

    async def get_all(self) -> list[Session]:
        return await self.dao.enumerate()

    async def end_session(self, session_id: Id) -> bool:
        return await self.dao.delete(session_id)

    async def end_sessions_for_user(self, user_id: Id) -> None:
        for session in await self.dao.list_for_user(user_id):
            await self.end_session(session.id)
