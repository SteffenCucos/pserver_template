
import asyncio

from unittest.mock import create_autospec

import pytest

from fastapi import HTTPException, status

# Imports the top-level persistence package before legacy absolute imports load session models.
from server.api import router as _router  # noqa: F401
from server.auth.authentication_service import AuthenticationService
from server.auth.password.password_service import PasswordService
from server.auth.session.session import Session
from server.auth.session.session_service import SessionService
from server.users.user import User
from server.users.user_service import UserService


def make_user() -> User:
    return User(
        user_name="alice",
        first_name="Alice",
        last_name="Example",
        password_hash="stored-hash",
        email="alice@example.com",
    )


def make_service() -> tuple[AuthenticationService, UserService, PasswordService, SessionService]:
    user_service = create_autospec(UserService, instance=True)
    password_service = create_autospec(PasswordService, instance=True)
    session_service = create_autospec(SessionService, instance=True)
    return (
        AuthenticationService(user_service, password_service, session_service),
        user_service,
        password_service,
        session_service,
    )


def test_authenticate_rejects_unknown_user() -> None:
    async def run_test() -> None:
        service, user_service, password_service, session_service = make_service()
        user_service.get_user_by_name.return_value = None

        with pytest.raises(HTTPException) as exception:
            await service.authenticate("unknown", "a secure password")

        assert exception.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exception.value.detail == "Incorrect user name or password"
        user_service.get_user_by_name.assert_awaited_once_with("unknown")
        password_service.verify_password.assert_not_called()
        session_service.create_session.assert_not_awaited()

    asyncio.run(run_test())


def test_authenticate_rejects_invalid_password() -> None:
    async def run_test() -> None:
        service, user_service, password_service, session_service = make_service()
        user = make_user()
        user_service.get_user_by_name.return_value = user
        password_service.verify_password.return_value = False

        with pytest.raises(HTTPException) as exception:
            await service.authenticate("alice", "wrong password")

        assert exception.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exception.value.detail == "Incorrect user name or password"
        password_service.verify_password.assert_called_once_with("stored-hash", "wrong password")
        password_service.needs_rehash.assert_not_called()
        session_service.create_session.assert_not_awaited()

    asyncio.run(run_test())


def test_authenticate_creates_session_without_rehashing_current_password_hash() -> None:
    async def run_test() -> None:
        service, user_service, password_service, session_service = make_service()
        user = make_user()
        session = Session(user_id=user.id)
        user_service.get_user_by_name.return_value = user
        password_service.verify_password.return_value = True
        password_service.needs_rehash.return_value = False
        session_service.create_session.return_value = session

        assert await service.authenticate("alice", "a secure password") is session

        password_service.needs_rehash.assert_called_once_with("stored-hash")
        password_service.hash_password.assert_not_called()
        user_service.update_password_hash.assert_not_awaited()
        session_service.create_session.assert_awaited_once_with(user)

    asyncio.run(run_test())


def test_authenticate_rehashes_password_before_creating_session_when_needed() -> None:
    async def run_test() -> None:
        service, user_service, password_service, session_service = make_service()
        user = make_user()
        session = Session(user_id=user.id)
        user_service.get_user_by_name.return_value = user
        password_service.verify_password.return_value = True
        password_service.needs_rehash.return_value = True
        password_service.hash_password.return_value = "new-hash"
        session_service.create_session.return_value = session

        assert await service.authenticate("alice", "a secure password") is session

        password_service.hash_password.assert_called_once_with("a secure password")
        user_service.update_password_hash.assert_awaited_once_with(user, "new-hash")
        session_service.create_session.assert_awaited_once_with(user)

    asyncio.run(run_test())
