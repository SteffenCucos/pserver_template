
"""Authentication annotation wired into FastAPI dependency injection."""

from api.authentication.endpoint_types import EndpointDecorator
from api.authentication.route_permissions import mark_auth_required


def authenticated() -> EndpointDecorator:
    """Mark a route as requiring an authenticated, non-expired session."""
    return mark_auth_required
