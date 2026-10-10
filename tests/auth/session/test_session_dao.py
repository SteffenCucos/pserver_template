
import asyncio

from unittest.mock import create_autospec

# Imports the top-level persistence package before the session model's legacy absolute imports.
from server.api import router as _router  # noqa: F401
from server.auth.session.session import Session
from server.auth.session.session_dao import SessionDAO
from server.models.base.id import Id
from server.persistence.repository import Repository


def test_list_for_user_filters_enumerated_sessions() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = SessionDAO(repository)
        matching_session = Session(user_id=Id("user-1"))
        other_session = Session(user_id=Id("user-2"))
        repository.enumerate.return_value = [matching_session, other_session]

        assert await dao.list_for_user(Id("user-1")) == [matching_session]

        repository.enumerate.assert_awaited_once_with(limit=-1, offset=0)

    asyncio.run(run_test())
