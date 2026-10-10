
import logging

from dataclasses import dataclass

from api.exceptions import UnprocessableEntityException
from auth.password.password_service import PasswordService
from models.base.id import Id
from users.user import User
from users.user_dao import UserDAO


logger = logging.getLogger(__name__)


@dataclass
class CreateUserRequest:
    user_name: str
    first_name: str
    last_name: str
    password: str
    email: str


@dataclass
class UpdateUserRequest:
    user_name: str | None = None
    password: str | None = None
    email: str | None = None


class UserService:
    """
    Manage users
    """
    def __init__(self, user_dao: UserDAO, password_service: PasswordService) -> None:
        self.user_dao = user_dao
        self.password_service = password_service

    async def create_user(self, user_request: CreateUserRequest) -> User:
        if await self.user_dao.get_by_name(user_request.user_name):
            raise UnprocessableEntityException("Username is already taken")

        if await self.user_dao.get_by_email(user_request.email):
            raise UnprocessableEntityException("Email is already in use.")

        if len(user_request.password) < 12 or not user_request.password.strip():
            raise UnprocessableEntityException("Password must be at least 12 characters")

        user = User(
            user_name=user_request.user_name,
            first_name=user_request.first_name,
            last_name=user_request.last_name,
            password_hash=self.password_service.hash_password(user_request.password),
            email=user_request.email,
        )
        return await self.user_dao.create(user)

    async def get_user(self, user_id: Id) -> User | None:
        return await self.user_dao.get_by_id(user_id)

    async def get_user_by_name(self, user_name: str) -> User | None:
        return await self.user_dao.get_by_name(user_name)

    async def get_all_users(self) -> list[User]:
        return await self.user_dao.enumerate()

    async def update_user(self, user: User, user_request: UpdateUserRequest) -> User:
        changes: dict[str, str] = {}

        if user_request.user_name is not None and user_request.user_name != user.user_name:
            existing_user = await self.user_dao.get_by_name(user_request.user_name)
            if existing_user and existing_user.id != user.id:
                raise UnprocessableEntityException("Username is already taken")
            changes["user_name"] = user_request.user_name

        if user_request.email is not None and user_request.email != user.email:
            existing_user = await self.user_dao.get_by_email(user_request.email)
            if existing_user and existing_user.id != user.id:
                raise UnprocessableEntityException("Email is already in use.")
            changes["email"] = user_request.email

        if user_request.password is not None:
            if len(user_request.password) < 12 or not user_request.password.strip():
                raise UnprocessableEntityException("Password must be at least 12 characters")
            changes["password_hash"] = self.password_service.hash_password(user_request.password)

        if not changes:
            return user

        updated_user = await self.user_dao.update(user.id, changes)
        return updated_user or user

    async def update_password_hash(self, user: User, password_hash: str) -> User:
        updated_user = await self.user_dao.update_password_hash(user.id, password_hash)
        return updated_user or user

    async def delete_user(self, user: User) -> bool:
        return await self.user_dao.delete(user.id)
