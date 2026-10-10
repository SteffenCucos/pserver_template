
import asyncio

from unittest.mock import create_autospec

from server.models.base.id import Id
from server.persistence.repository import Repository
from server.users.user import User
from server.users.user_dao import UserDAO


def make_user(user_name: str = "alice", email: str = "alice@example.com") -> User:
    return User(
        user_name=user_name,
        first_name="Alice",
        last_name="Example",
        password_hash="password-hash",
        email=email,
    )


def test_get_by_name_queries_repository_by_username() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = UserDAO(repository)
        user = make_user()
        repository.find_one.return_value = user

        assert await dao.get_by_name("alice") is user

        repository.find_one.assert_awaited_once_with({"user_name": "alice"})

    asyncio.run(run_test())


def test_get_by_email_queries_repository_by_email() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = UserDAO(repository)
        user = make_user()
        repository.find_one.return_value = user

        assert await dao.get_by_email("alice@example.com") is user

        repository.find_one.assert_awaited_once_with({"email": "alice@example.com"})

    asyncio.run(run_test())


def test_update_password_hash_updates_only_the_hash() -> None:
    async def run_test() -> None:
        repository = create_autospec(Repository, instance=True)
        dao = UserDAO(repository)
        user_id = Id("user-id")
        updated_user = make_user()
        repository.update.return_value = updated_user

        assert await dao.update_password_hash(user_id, "new-password-hash") is updated_user

        repository.update.assert_awaited_once()
        entity_id, changes = repository.update.await_args.args
        assert entity_id == "user-id"
        assert changes["password_hash"] == "new-password-hash"
        assert "_updated_date" in changes

    asyncio.run(run_test())
