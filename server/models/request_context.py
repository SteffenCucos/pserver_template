
from __future__ import annotations

from dataclasses import dataclass

from auth.session.session import Session
from models.base.id import Id
from users.user import User


@dataclass
class RequestContext():
    """
    Holds relevant information that is set at the request root
    """
    session_id: Id | None = None
    session: Session | None = None
    session_expired: bool | None = None
    current_user_id: Id | None = None
    current_user: User | None = None
    filled: bool | None = None

    def __getattr__(self, name: str) -> object | None:
        return self.__dict__.get(name, None)
