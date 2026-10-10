
import logging

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from api.exceptions import NotFoundException
from api.router import Router
from api.v1 import base_route
from auth.dependencies import (
    get_permission_service,
    get_role_permission_dao,
    get_role_service,
    get_user_role_dao,
)
from auth.rbac.daos.role_permission_dao import RolePermissionDAO
from auth.rbac.daos.user_role_dao import UserRoleDAO
from auth.rbac.models import Role, RolePermission, UserRole
from auth.rbac.permission_service import PermissionService
from auth.rbac.role_service import RoleService
from models.base.id import Id
from users.dependencies import get_user_service
from users.user_service import UserService


logger = logging.getLogger(__name__)

router = Router(
    prefix=base_route + "/roles",
)

@dataclass
class RoleRequest:
    description: str
    name: str


@dataclass
class RolePermissionDTO:
    id: Id
    role_id: Id
    permission_id: Id
    permission: str


@router.get("", response_model=None)
async def list_roles(
    role_service: Annotated[RoleService, Depends(get_role_service)]
) -> list[Role]:
    return await role_service.enumerate_rolls()

@router.post("")
async def create_role(
    role_request: RoleRequest,
    role_service: Annotated[RoleService, Depends(get_role_service),]
) -> str:
    role = await role_service.create_or_update_role(
        description=role_request.description,
        name=role_request.name,
    )
    return str(role.id)

@router.get("/{role_id}/permissions", response_model=None)
async def get_permission_roles(
    role_id: str,
    role_permission_dao: Annotated[RolePermissionDAO, Depends(get_role_permission_dao)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)]
) -> list[RolePermissionDTO]:
    role_permissions: list[RolePermissionDTO] = []
    role_id = Id(role_id)
    for role_permission in await role_permission_dao.list_for_role(role_id):
        permission = await permission_service.get_permission(role_permission.permission_id)
        if not permission:
            continue
        role_permissions.append(RolePermissionDTO(
            role_permission.id,
            role_permission.role_id,
            permission.id,
            permission.key
        ))

    return role_permissions

@router.post("/{role_id}/permission/{permission_id}")
async def create_permission_role(
    role_id: str,
    permission_id: str,
    role_service: Annotated[RoleService, Depends(get_role_service)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    role_permission_dao: Annotated[RolePermissionDAO, Depends(get_role_permission_dao)]
) -> str:
    role_id = Id(role_id)
    permission_id = Id(permission_id)

    role = await role_service.get_role(role_id)
    if not role:
        raise  NotFoundException(f"Role {role_id} not found.")
    
    permission = await permission_service.get_permission(permission_id)
    if not permission:
        raise NotFoundException(f"Permission {permission_id} not found.")

    role_permission = await role_permission_dao.create(
        RolePermission(role_id, permission_id)
    )

    return str(role_permission.id)

@router.delete("/{role_id}/permission/{permission_id}")
async def delete_permission_role(
    role_id: str,
    permission_id: str,
    role_permission_dao: Annotated[RolePermissionDAO, Depends(get_role_permission_dao)]
) -> str:
    role_permission = await role_permission_dao.find_one({ "role_id": role_id, "permission_id": permission_id })
    if not role_permission:
        raise NotFoundException(f"RolePermission not found for RoleId:{role_id} | PermissionId:{permission_id}")
    
    await role_permission_dao.delete(role_permission.id)
    return str(role_permission.id)

@router.get("/{role_id}/users", response_model=None)
async def get_users_for_role(
    role_id: str,
    role_service: Annotated[RoleService, Depends(get_role_service)],
    user_role_dao: Annotated[UserRoleDAO, Depends(get_user_role_dao)]
) -> list[UserRole]:
    role_id = Id(role_id)
    role = await role_service.get_role(role_id)
    if not role:
        raise NotFoundException(f"Role {role_id} not found.")

    return await user_role_dao.find_all({"role_id": role_id})

@router.get("/{user_id}", response_model=None)
async def get_roles_for_user(
    user_id: str,
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_role_dao: Annotated[UserRoleDAO, Depends(get_user_role_dao)]
) -> list[UserRole]:
    user_id = Id(user_id)
    user = await user_service.get_user(user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")

    return await user_role_dao.find_all({"user_id": user_id})


@router.post("/{role_id}/user/{user_id}")
async def add_user_to_role(
    role_id: str,
    user_id: str,
    role_service: Annotated[RoleService, Depends(get_role_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_role_dao: Annotated[UserRoleDAO, Depends(get_user_role_dao)]
) -> str:
    role_id = Id(role_id)
    user_id = Id(user_id)
    role = await role_service.get_role(role_id)
    if not role:
        raise NotFoundException(f"Role {role_id} not found.")
    
    user = await user_service.get_user(user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")

    user_role = await user_role_dao.create(UserRole(user_id, role_id))
    return str(user_role.id)
