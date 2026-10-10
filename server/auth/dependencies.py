
"""FastAPI dependency providers for auth domain services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from persistence.dependencies import repository_dependency
from persistence.pserialize_entity_serializer import PSerializeEntitySerializer
from persistence.repository import Repository

from auth.rbac import Permission as PermModel
from auth.rbac import Role, RolePermission, UserRole
from auth.rbac.authorization_tree_service import AuthorizationTreeService
from auth.rbac.permission_service import PermissionService
from auth.rbac.role_service import RoleService
from users.dependencies import get_user_service
from users.user_service import UserService

from .authentication_service import AuthenticationService
from .authorization_service import AuthorizationService
from .password.dependencies import get_password_service
from .password.password_service import PasswordService
from .rbac.daos import PermissionDAO, RoleDAO, RolePermissionDAO, UserRoleDAO
from .session.session import Session
from .session.session_dao import SessionDAO
from .session.session_service import SessionService


get_perm_repository = repository_dependency(
    resource_name="perms",
    serializer=PSerializeEntitySerializer(PermModel),
)


get_role_repository = repository_dependency(
    resource_name="roles",
    serializer=PSerializeEntitySerializer(Role),
)


get_user_role_repository = repository_dependency(
    resource_name="user_roles",
    serializer=PSerializeEntitySerializer(UserRole),
)


get_role_perm_repository = repository_dependency(
    resource_name="role_perms",
    serializer=PSerializeEntitySerializer(RolePermission),
)


get_session_repository = repository_dependency(
    resource_name="sessions",
    serializer=PSerializeEntitySerializer(Session),
)


def get_permission_dao(
    repository: Annotated[Repository[PermModel], Depends(get_perm_repository)],
) -> PermissionDAO:
    return PermissionDAO(repository)


def get_role_dao(
    repository: Annotated[Repository[Role], Depends(get_role_repository)],
) -> RoleDAO:
    return RoleDAO(repository)


def get_user_role_dao(
    repository: Annotated[Repository[UserRole], Depends(get_user_role_repository)],
) -> UserRoleDAO:
    return UserRoleDAO(repository)


def get_role_permission_dao(
    repository: Annotated[Repository[RolePermission], Depends(get_role_perm_repository)],
) -> RolePermissionDAO:
    return RolePermissionDAO(repository)


def get_session_dao(
    repository: Annotated[Repository[Session], Depends(get_session_repository)],
) -> SessionDAO:
    return SessionDAO(repository)


def get_session_service(session_dao: Annotated[SessionDAO, Depends(get_session_dao)]) -> SessionService:
    return SessionService(session_dao)


def get_authentication_service(
    user_service: Annotated[UserService, Depends(get_user_service)],
    password_service: Annotated[PasswordService, Depends(get_password_service)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> AuthenticationService:
    return AuthenticationService(user_service, password_service, session_service)


def get_permission_service(
    permission_dao: Annotated[PermissionDAO, Depends(get_permission_dao)],
) -> PermissionService:
    return PermissionService(permission_dao)


def get_role_service(
    role_dao: Annotated[RoleDAO, Depends(get_role_dao)],
) -> RoleService:
    return RoleService(role_dao)


def get_authorization_tree_service(
    user_role_dao: Annotated[UserRoleDAO, Depends(get_user_role_dao)],
    role_permission_dao: Annotated[RolePermissionDAO, Depends(get_role_permission_dao)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> AuthorizationTreeService:
    return AuthorizationTreeService(user_role_dao, role_permission_dao, permission_service)


def get_authorization_service(
    role_permission_dao: Annotated[RolePermissionDAO, Depends(get_role_permission_dao)],
    user_role_dao: Annotated[UserRoleDAO, Depends(get_user_role_dao)],
    role_service: Annotated[RoleService, Depends(get_role_service)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    authorization_tree_service: Annotated[AuthorizationTreeService, Depends(get_authorization_tree_service)],
) -> AuthorizationService:
    return AuthorizationService(
        role_permission_dao, user_role_dao, role_service, permission_service, authorization_tree_service
    )
