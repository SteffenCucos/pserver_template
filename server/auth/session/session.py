
from dataclasses import dataclass, field
from datetime import datetime as Datetime
from datetime import timedelta

from models.base.entity import Entity
from models.base.id import Id


@dataclass
class Session(Entity()):  # type: ignore[misc]
    user_id: Id
    expires_at: Datetime = field(default_factory=lambda: Datetime.now() + timedelta(hours=1))

    def is_expired(self) -> bool:
        return self.expires_at < Datetime.now()
