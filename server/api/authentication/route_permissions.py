
"""Internal metadata attached by the public auth decorators."""

from dataclasses import dataclass
from typing import Any

from .endpoint_types import EndpointDecorator, EndpointT


_AUTH_REQUIRED_ATTRIBUTE = "__server_template_auth_required__"
_PERMISSION_REQUIREMENT_ATTRIBUTE = "__server_template_permission_requirement__"


@dataclass(frozen=True)
class PermissionRequirement:
    permission: str


def mark_auth_required(endpoint: EndpointT) -> EndpointT:
    """Attach authentication metadata to an endpoint."""
    setattr(endpoint, _AUTH_REQUIRED_ATTRIBUTE, True)
    return endpoint


def mark_permission_required(
    permission: str,
) -> EndpointDecorator:
    """Attach one permission template to an endpoint."""
    normalized = permission.strip()
    if not normalized:
        raise ValueError("A non-empty permission is required")

    requirement = PermissionRequirement(permission=normalized)

    def mark_endpoint(endpoint: EndpointT) -> EndpointT:
        mark_auth_required(endpoint)
        setattr(endpoint, _PERMISSION_REQUIREMENT_ATTRIBUTE, requirement)
        return endpoint

    return mark_endpoint


def get_auth_required(endpoint: Any) -> bool:
    return bool(getattr(endpoint, _AUTH_REQUIRED_ATTRIBUTE, False))


def get_permission_requirement(
    endpoint: Any,
) -> PermissionRequirement | None:
    return getattr(endpoint, _PERMISSION_REQUIREMENT_ATTRIBUTE, None)
