
from uuid import uuid4

from fastapi.testclient import TestClient
from test_users_api import _create_permission, _create_role, _grant_permission


def test_create_permission_returns_a_persisted_permission_id(client: TestClient) -> None:
    permission_key = f"read/widgets/{uuid4().hex}"

    permission_id = _create_permission(client, permission_key)

    assert isinstance(permission_id, str)
    assert permission_id

    # Associate the permission with a role and retrieve it through the API to
    # verify that the permission-creation request persisted server-side.
    role_id = _create_role(client, f"role_{uuid4().hex}")
    _grant_permission(client, role_id, permission_id)
    response = client.get(f"/api/v1/roles/{role_id}/permissions")

    assert response.status_code == 200, response.text
    assert any(
        permission["permission_id"] == permission_id and permission["permission"] == permission_key
        for permission in response.json()
    )
