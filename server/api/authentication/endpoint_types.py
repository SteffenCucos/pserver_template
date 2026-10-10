
"""Shared typing primitives for auth-aware endpoint decorators and routes."""

from collections.abc import Callable
from typing import Any, Protocol, TypeVar


EndpointT = TypeVar("EndpointT", bound=Callable[..., Any])


class EndpointDecorator(Protocol):
    def __call__(self, endpoint: EndpointT, /) -> EndpointT:
        ...
