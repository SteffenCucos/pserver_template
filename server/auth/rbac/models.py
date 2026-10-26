
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Union

from persistence.models import FOREIGN_KEY, INDEX, NOT_NULLABLE, UNIQUE, field
from persistence.repository.sql.schema.types import UniqueConstraint

from models.base.entity import Entity
from models.base.id import Id


@dataclass
class Permission(Entity()):  # type: ignore[misc]
    key: str = field(NOT_NULLABLE | INDEX)
    description: Union[str, None] = None

    table_name: ClassVar[str] = "permissions"
    unique_constraints: ClassVar[list[UniqueConstraint]] = [UniqueConstraint("uq_permission_key", ["key"])]


@dataclass
class Role(Entity("name")):  # type: ignore[misc]
    name: str = field(NOT_NULLABLE | INDEX | UNIQUE)
    description: Union[str, None] = None

    table_name: ClassVar[str] = "roles"


@dataclass
class UserRole(Entity()):  # type: ignore[misc]
    user_id: Id = field(NOT_NULLABLE | INDEX | FOREIGN_KEY("users.id"))
    role_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("roles.id"))

    table_name: ClassVar[str] = "user_roles"
    unique_constraints: ClassVar[list[UniqueConstraint]] = [UniqueConstraint("uq_user_role_user_id_role_id", ["user_id", "role_id"])]


@dataclass
class RolePermission(Entity()):  # type: ignore[misc]
    role_id: Id = field(NOT_NULLABLE | INDEX | FOREIGN_KEY("roles.id"))
    permission_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("permissions.id"))

    table_name: ClassVar[str] = "role_permissions"
    unique_constraints: ClassVar[list[UniqueConstraint]] = [UniqueConstraint("uq_role_permission_role_id_permission_id", ["role_id", "permission_id"])]
