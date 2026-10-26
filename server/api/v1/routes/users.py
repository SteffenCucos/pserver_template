
import logging

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Depends

from api.authentication.dependencies import require_current_user
from api.decorators.check_permissions import check_permission
from api.exceptions import NotFoundException
from api.router import Router
from api.v1 import base_route
from auth.authorization_service import AuthorizationService
from auth.dependencies import get_authorization_service, get_session_service
from auth.session.session_service import SessionService
from models.base.id import Id
from users.dependencies import get_user_service
from users.user import User
from users.user_service import CreateUserRequest, UpdateUserRequest, UserService


logger = logging.getLogger(__name__)

router = Router(
    prefix=base_route + "/users",
)


@dataclass
class UserResponse:
    id: str
    created_date: datetime
    updated_date: datetime
    user_name: str
    email: str
    email_verified: bool


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        created_date=user.created_date,
        updated_date=user.updated_date,
        user_name=user.user_name,
        email=user.email,
        email_verified=user.email_verified,
    )


@router.post("")
async def create_user(
    user_request: CreateUserRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> str:
    user = await user_service.create_user(user_request)
    return str(user.id)


@router.get("")
async def get_all_users(
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(require_current_user)],
    authorization_service: Annotated[
        AuthorizationService,
        Depends(get_authorization_service),
    ],
) -> list[UserResponse]:
    all_users = await user_service.get_all_users()

    # Filter out all users the calling user doesn't have permission to see
    filtered: list[User] = []
    for user in all_users:
        permission = f"read/users/{user.id}"
        if await authorization_service.user_has_access(current_user.id, permission):
            filtered.append(user)

    return [_to_user_response(user) for user in filtered]


@router.get("/{user_id}")
@check_permission("read/users/{user_id}")
async def get_user(
    user_id: str,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    user_id = Id(user_id)
    user = await user_service.get_user(user_id)
    if not user:
        raise NotFoundException(f"User with id:{user_id} does not exist")

    return _to_user_response(user)


@router.patch("/{user_id}")
@check_permission("write/users/{user_id}")
async def update_user(
    user_id: str,
    user_request: UpdateUserRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    user_id = Id(user_id)
    user = await user_service.get_user(user_id)
    if not user:
        raise NotFoundException(f"User with id:{user_id} does not exist")

    updated_user = await user_service.update_user(user, user_request)
    return _to_user_response(updated_user)


@router.delete("/{user_id}")
@check_permission("delete/users/{user_id}")
async def delete_user(
    user_id: str,
    user_service: Annotated[UserService, Depends(get_user_service)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> UserResponse:
    user_id = Id(user_id)
    user = await user_service.get_user(user_id)
    if not user:
        raise NotFoundException(f"User with id:{user_id} does not exist")

    # Find any sessions associated with the user and delete them
    await session_service.end_sessions_for_user(user_id)

    await user_service.delete_user(user)
    return _to_user_response(user)
