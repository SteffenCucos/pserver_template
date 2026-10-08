
from __future__ import annotations

from dataclasses import dataclass
from typing import Union, override

from persistence.models import FOREIGN_KEY, INDEX, NOT_NULLABLE, UNIQUE, field

from models.base.entity import Entity
from models.base.id import Id


@dataclass
class Permission(Entity()):  # type: ignore[misc]
    key: str = field(NOT_NULLABLE | INDEX())
    description: Union[str, None] = None

    @override
    @staticmethod
    def table_name() -> str:
        return "permissions"


@dataclass
class Role(Entity("name")):  # type: ignore[misc]
    name: str = field(NOT_NULLABLE | INDEX() | UNIQUE)
    description: Union[str, None] = None

    @override
    @staticmethod
    def table_name() -> str:
        return "roles"


@dataclass
class UserRole(Entity()):  # type: ignore[misc]
    user_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("users.id"))
    role_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("roles.id"))

    @override
    @staticmethod
    def table_name() -> str:
        return "user_roles"


@dataclass
class RolePermission(Entity()):  # type: ignore[misc]
    role_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("roles.id"))
    permission_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("permissions.id"))

    @override
    @staticmethod
    def table_name() -> str:
        return "role_permissions"
