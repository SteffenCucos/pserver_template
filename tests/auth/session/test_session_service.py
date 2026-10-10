
import asyncio

from unittest.mock import call, create_autospec

# Imports the top-level persistence package before the session model's legacy absolute imports.
from server.api import router as _router  # noqa: F401
from server.auth.session.session import Session
from server.auth.session.session_dao import SessionDAO
from server.auth.session.session_service import SessionService
from server.models.base.id import Id
from server.users.user import User


def make_user() -> User:
    return User(
        user_name="alice",
        first_name="Alice",
        last_name="Example",
        password_hash="password-hash",
        email="alice@example.com",
    )


def test_create_session_persists_a_session_for_the_user() -> None:
    async def run_test() -> None:
        dao = create_autospec(SessionDAO, instance=True)
        service = SessionService(dao)
        user = make_user()
        created_session = Session(user_id=user.id)
        dao.create.return_value = created_session

        assert await service.create_session(user) is created_session

        dao.create.assert_awaited_once()
        session_to_create = dao.create.await_args.args[0]
        assert session_to_create.user_id == user.id

    asyncio.run(run_test())


def test_get_all_and_end_session_delegate_to_dao() -> None:
    async def run_test() -> None:
        dao = create_autospec(SessionDAO, instance=True)
        service = SessionService(dao)
        session = Session(user_id=Id("user-1"))
        session_id = Id("session-id")
        dao.get_by_id.return_value = session
        dao.enumerate.return_value = [session]
        dao.delete.return_value = True

        assert await service.get_session(session_id) is session
        assert await service.get_all() == [session]
        assert await service.end_session(session_id) is True

        dao.get_by_id.assert_awaited_once_with(session_id)
        dao.enumerate.assert_awaited_once_with()
        dao.delete.assert_awaited_once_with(session_id)

    asyncio.run(run_test())


def test_end_sessions_for_user_deletes_every_session_belonging_to_user() -> None:
    async def run_test() -> None:
        dao = create_autospec(SessionDAO, instance=True)
        service = SessionService(dao)
        user_id = Id("user-1")
        first_session = Session(user_id=user_id)
        second_session = Session(user_id=user_id)
        dao.list_for_user.return_value = [first_session, second_session]

        assert await service.end_sessions_for_user(user_id) is None

        dao.list_for_user.assert_awaited_once_with(user_id)
        dao.delete.assert_has_awaits([call(first_session.id), call(second_session.id)])

    asyncio.run(run_test())
