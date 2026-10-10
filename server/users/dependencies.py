
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from persistence.dependencies import repository_dependency
from persistence.pserialize_entity_serializer import PSerializeEntitySerializer
from persistence.repository.repository import Repository

from auth.password.dependencies import get_password_service
from auth.password.password_service import PasswordService

from .user import User
from .user_dao import UserDAO
from .user_service import UserService


get_user_repository = repository_dependency(
    resource_name="users",
    serializer=PSerializeEntitySerializer(User),
)

def get_user_dao(
    repository: Annotated[Repository[User], Depends(get_user_repository)],
) -> UserDAO:
    return UserDAO(repository)

def get_user_service(
    user_dao: Annotated[UserDAO, Depends(get_user_dao)],
    password_service: Annotated[PasswordService, Depends(get_password_service)],
) -> UserService:
    return UserService(user_dao, password_service)
