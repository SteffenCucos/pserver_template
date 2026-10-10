
from uuid import uuid4

from fastapi.testclient import TestClient
from test_users_api import (
    _assign_role,
    _create_permission,
    _create_role,
    _create_user,
    _grant_permission,
    _unique_user_payload,
)


def test_create_role_and_list_roles(client: TestClient) -> None:
    role_name = f"role_{uuid4().hex}"

    role_id = _create_role(client, role_name)
    response = client.get("/api/v1/roles")

    assert response.status_code == 200, response.text
    assert any(role["id"] == role_id and role["name"] == role_name for role in response.json())


def test_manage_role_permissions_and_users_through_api(client: TestClient) -> None:
    payload = _unique_user_payload()
    user_id = _create_user(client, payload)
    role_id = _create_role(client, f"role_{uuid4().hex}")
    permission_key = f"read/widgets/{uuid4().hex}"
    permission_id = _create_permission(client, permission_key)

    _grant_permission(client, role_id, permission_id)
    permissions_response = client.get(f"/api/v1/roles/{role_id}/permissions")

    assert permissions_response.status_code == 200, permissions_response.text
    assert any(
        permission["permission_id"] == permission_id and permission["permission"] == permission_key
        for permission in permissions_response.json()
    )

    _assign_role(client, role_id, user_id)
    role_users_response = client.get(f"/api/v1/roles/{role_id}/users")
    user_roles_response = client.get(f"/api/v1/roles/{user_id}")

    assert role_users_response.status_code == 200, role_users_response.text
    assert any(
        relation["user_id"] == user_id and relation["role_id"] == role_id
        for relation in role_users_response.json()
    )
    assert user_roles_response.status_code == 200, user_roles_response.text
    assert any(
        relation["user_id"] == user_id and relation["role_id"] == role_id
        for relation in user_roles_response.json()
    )

    delete_response = client.delete(f"/api/v1/roles/{role_id}/permission/{permission_id}")
    assert delete_response.status_code == 200, delete_response.text

    permissions_after_delete = client.get(f"/api/v1/roles/{role_id}/permissions")
    assert permissions_after_delete.status_code == 200, permissions_after_delete.text
    assert all(permission["permission_id"] != permission_id for permission in permissions_after_delete.json())
