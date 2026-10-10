
from dataclasses import dataclass

from persistence.models import INDEX, NOT_NULLABLE, UNIQUE, field
from typing_extensions import override

from models.base.entity import Entity


@dataclass
class User(Entity()):  # type: ignore[misc]
    user_name: str = field(NOT_NULLABLE | INDEX())
    first_name: str = field(NOT_NULLABLE)
    last_name: str  = field(NOT_NULLABLE)
    password_hash: str = field(NOT_NULLABLE)
    email: str = field(NOT_NULLABLE | UNIQUE | INDEX())
    email_verified: bool = False

    @staticmethod
    @override
    def table_name() -> str:
        return "users"
