
import asyncio

from unittest.mock import create_autospec

import pytest

from server.auth.password.password_service import PasswordService
from server.models.base.id import Id
from server.users.user import User
from server.users.user_dao import UserDAO
from server.users.user_service import CreateUserRequest, UpdateUserRequest, UserService


def make_user(user_name: str = "alice", email: str = "alice@example.com") -> User:
    return User(
        user_name=user_name,
        first_name="Alice",
        last_name="Example",
        password_hash="existing-hash",
        email=email,
    )


def make_service() -> tuple[UserService, UserDAO, PasswordService]:
    user_dao = create_autospec(UserDAO, instance=True)
    password_service = create_autospec(PasswordService, instance=True)
    return UserService(user_dao, password_service), user_dao, password_service


def test_create_user_hashes_password_and_persists_user() -> None:
    async def run_test() -> None:
        service, user_dao, password_service = make_service()
        request = CreateUserRequest(
            user_name="alice",
            first_name="Alice",
            last_name="Example",
            password="a secure password",
            email="alice@example.com",
        )
        created_user = make_user()
        user_dao.get_by_name.return_value = None
        user_dao.get_by_email.return_value = None
        user_dao.create.return_value = created_user
        password_service.hash_password.return_value = "hashed-password"

        assert await service.create_user(request) is created_user

        user_dao.get_by_name.assert_awaited_once_with("alice")
        user_dao.get_by_email.assert_awaited_once_with("alice@example.com")
        password_service.hash_password.assert_called_once_with("a secure password")
        user_dao.create.assert_awaited_once()
        persisted_user = user_dao.create.await_args.args[0]
        assert persisted_user.user_name == "alice"
        assert persisted_user.first_name == "Alice"
        assert persisted_user.last_name == "Example"
        assert persisted_user.email == "alice@example.com"
        assert persisted_user.password_hash == "hashed-password"

    asyncio.run(run_test())


@pytest.mark.parametrize(
    ("existing_field", "detail"),
    [
        ("get_by_name", "Username is already taken"),
        ("get_by_email", "Email is already in use."),
    ],
)
def test_create_user_rejects_existing_username_or_email(existing_field: str, detail: str) -> None:
    async def run_test() -> None:
        service, user_dao, password_service = make_service()
        request = CreateUserRequest("alice", "Alice", "Example", "a secure password", "a@example.com")
        user_dao.get_by_name.return_value = None
        getattr(user_dao, existing_field).return_value = make_user()

        with pytest.raises(Exception, match=detail):
            await service.create_user(request)

        password_service.hash_password.assert_not_called()
        user_dao.create.assert_not_awaited()

    asyncio.run(run_test())


@pytest.mark.parametrize("password", ["short", "            "])
def test_create_user_rejects_invalid_password(password: str) -> None:
    async def run_test() -> None:
        service, user_dao, password_service = make_service()
        user_dao.get_by_name.return_value = None
        user_dao.get_by_email.return_value = None
        request = CreateUserRequest("alice", "Alice", "Example", password, "a@example.com")

        with pytest.raises(Exception, match="Password must be at least 12 characters"):
            await service.create_user(request)

        password_service.hash_password.assert_not_called()
        user_dao.create.assert_not_awaited()

    asyncio.run(run_test())


def test_read_methods_delegate_to_user_dao() -> None:
    async def run_test() -> None:
        service, user_dao, _ = make_service()
        user = make_user()
        user_id = Id("user-id")
        user_dao.get_by_id.return_value = user
        user_dao.get_by_name.return_value = user
        user_dao.enumerate.return_value = [user]

        assert await service.get_user(user_id) is user
        assert await service.get_user_by_name("alice") is user
        assert await service.get_all_users() == [user]

        user_dao.get_by_id.assert_awaited_once_with(user_id)
        user_dao.get_by_name.assert_awaited_once_with("alice")
        user_dao.enumerate.assert_awaited_once_with()

    asyncio.run(run_test())


def test_update_user_applies_changed_name_email_and_password() -> None:
    async def run_test() -> None:
        service, user_dao, password_service = make_service()
        user = make_user()
        updated_user = make_user("bob", "bob@example.com")
        request = UpdateUserRequest("bob", "a new secure password", "bob@example.com")
        user_dao.get_by_name.return_value = None
        user_dao.get_by_email.return_value = None
        user_dao.update.return_value = updated_user
        password_service.hash_password.return_value = "new-hash"

        assert await service.update_user(user, request) is updated_user

        user_dao.get_by_name.assert_awaited_once_with("bob")
        user_dao.get_by_email.assert_awaited_once_with("bob@example.com")
        password_service.hash_password.assert_called_once_with("a new secure password")
        user_dao.update.assert_awaited_once_with(
            user.id,
            {"user_name": "bob", "email": "bob@example.com", "password_hash": "new-hash"},
        )

    asyncio.run(run_test())


@pytest.mark.parametrize(
    ("update_request", "lookup", "detail"),
    [
        (UpdateUserRequest(user_name="bob"), "get_by_name", "Username is already taken"),
        (UpdateUserRequest(email="bob@example.com"), "get_by_email", "Email is already in use."),
    ],
)
def test_update_user_rejects_values_owned_by_another_user(
    update_request: UpdateUserRequest, lookup: str, detail: str
) -> None:
    async def run_test() -> None:
        service, user_dao, _ = make_service()
        getattr(user_dao, lookup).return_value = make_user("other", "other@example.com")

        with pytest.raises(Exception, match=detail):
            await service.update_user(make_user(), update_request)

        user_dao.update.assert_not_awaited()

    asyncio.run(run_test())


def test_update_user_returns_original_when_unchanged() -> None:
    async def run_test() -> None:
        service, user_dao, password_service = make_service()
        user = make_user()

        assert await service.update_user(user, UpdateUserRequest()) is user
        assert await service.update_user(
            user, UpdateUserRequest(user_name="alice", email="alice@example.com")
        ) is user

        user_dao.get_by_name.assert_not_awaited()
        user_dao.get_by_email.assert_not_awaited()
        password_service.hash_password.assert_not_called()
        user_dao.update.assert_not_awaited()

    asyncio.run(run_test())


def test_update_user_rejects_invalid_password_and_falls_back_when_dao_returns_none() -> None:
    async def run_test() -> None:
        service, user_dao, password_service = make_service()
        user = make_user()

        with pytest.raises(Exception, match="Password must be at least 12 characters"):
            await service.update_user(user, UpdateUserRequest(password="short"))

        password_service.hash_password.return_value = "new-hash"
        user_dao.update.return_value = None
        assert await service.update_user(user, UpdateUserRequest(password="a new secure password")) is user
        user_dao.update.assert_awaited_once_with(user.id, {"password_hash": "new-hash"})

    asyncio.run(run_test())


def test_update_password_hash_and_delete_delegate_to_user_dao() -> None:
    async def run_test() -> None:
        service, user_dao, _ = make_service()
        user = make_user()
        updated_user = make_user()
        user_dao.update_password_hash.return_value = updated_user
        user_dao.delete.return_value = True

        assert await service.update_password_hash(user, "replacement-hash") is updated_user
        assert await service.delete_user(user) is True

        user_dao.update_password_hash.assert_awaited_once_with(user.id, "replacement-hash")
        user_dao.delete.assert_awaited_once_with(user.id)

    asyncio.run(run_test())
