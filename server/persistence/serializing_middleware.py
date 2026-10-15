
from datetime import datetime
from typing import Callable, cast

from pserialize import Deserializer, Serializer


def get_application_serializer() -> Serializer:
    def serializer(obj: datetime, middleware: dict[type, Callable[[object], type]] = {}) -> str:
        return obj.isoformat()

    return Serializer(
        middleware={
            datetime: cast(Callable[[object], type], serializer)
        }
    )


def get_application_deserializer() -> Deserializer:
    def deserializer(value: str, middleware: dict[type, Callable[[object], type]] = {}) -> datetime:
        return datetime.fromisoformat(value)
        
    return Deserializer(
        middleware={
            datetime: cast(Callable[[object], type], deserializer)
        }
    )
