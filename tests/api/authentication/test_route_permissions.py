
from server.api.authentication.route_permissions import (
    get_auth_required,
    get_permission_requirement,
)
from server.api.decorators.authenticated import authenticated
from server.api.decorators.check_permissions import check_permission


def test_authenticated_marks_endpoint() -> None:
    def endpoint() -> None:
        pass

    decorated = authenticated()(endpoint)

    assert decorated is endpoint
    assert get_auth_required(endpoint)
    assert get_permission_requirement(endpoint) is None


def test_check_permission_stores_metadata_and_requires_auth() -> None:
    def endpoint() -> None:
        pass

    decorated = check_permission("read/users/{user_id}")(endpoint)

    assert decorated is endpoint
    assert get_auth_required(endpoint)
    requirement = get_permission_requirement(endpoint)
    assert requirement is not None
    assert requirement.permission == "read/users/{user_id}"


def test_check_permission_rejects_empty_permission() -> None:
    try:
        check_permission("   ")
    except ValueError as error:
        assert str(error) == "A non-empty permission is required"
    else:
        raise AssertionError("check_permission should reject an empty permission")
