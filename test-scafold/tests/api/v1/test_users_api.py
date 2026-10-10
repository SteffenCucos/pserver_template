
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def _unique_user_payload() -> dict[str, str]:
    suffix = uuid4().hex
    return {
        "user_name": f"user_{suffix}",
        "first_name": f"user_{suffix}_first_name",
        "last_name": f"user_{suffix}_last_name",
        "password": "correct-horse-battery-staple",
        "email": f"user_{suffix}@example.com",
    }


def _create_user(client: TestClient, payload: dict[str, str]) -> str:
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body
    return body["id"] if isinstance(body, dict) else body


def _login(client: TestClient, payload: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/sessions/login",
        json={"user_name": payload["user_name"], "password": payload["password"]},
    )
    assert response.status_code == 200, response.text
    session_id = response.json()
    assert isinstance(session_id, str)
    assert session_id
    client.cookies.set("session_id", session_id)
    return session_id


def _create_permission(client: TestClient, key: str) -> str:
    response = client.post(
        "/api/v1/permissions",
        json={"description": key, "permission": key},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_role(client: TestClient, name: str) -> str:
    response = client.post(
        "/api/v1/roles",
        json={"description": name, "name": name},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _grant_permission(client: TestClient, role_id: str, permission_id: str) -> None:
    response = client.post(
        f"/api/v1/roles/{role_id}/permission/{permission_id}",
    )
    assert response.status_code == 200, response.text


def _assign_role(client: TestClient, role_id: str, user_id: str) -> None:
    response = client.post(f"/api/v1/roles/{role_id}/user/{user_id}")
    assert response.status_code == 200, response.text


def _configure_permissions(
    client: TestClient,
    user_id: str,
    permission_keys: list[str],
) -> None:
    role_id = _create_role(client, f"role_{uuid4().hex}")
    for key in permission_keys:
        permission_id = _create_permission(client, key)
        _grant_permission(client, role_id, permission_id)
    _assign_role(client, role_id, user_id)


def test_health_reports_running_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200, response.text
    assert response.json() == {"running": True, "database": True}


def test_create_and_list_users(client: TestClient) -> None:
    payload = _unique_user_payload()
    user_id = _create_user(client, payload)

    assert isinstance(user_id, str)
    assert user_id

    _configure_permissions(client, user_id, [f"read/users/{user_id}"])
    _login(client, payload)
    response = client.get("/api/v1/users")
    assert response.status_code == 200, response.text
    users = response.json()

    assert any(user["user_name"] == payload["user_name"] for user in users)
    assert any(user["email"] == payload["email"] for user in users)


def test_duplicate_user_name_is_rejected(client: TestClient) -> None:
    payload = _unique_user_payload()
    _create_user(client, payload)

    duplicate = dict(payload)
    duplicate["email"] = f"other_{uuid4().hex}@example.com"
    response = client.post("/api/v1/users", json=duplicate)

    assert response.status_code == 422, response.text
    assert "Username is already taken" in response.text


def test_login_creates_session_and_session_listing_shows_user(client: TestClient) -> None:
    payload = _unique_user_payload()
    _create_user(client, payload)

    session_id = _login(client, payload)
    assert session_id

    sessions_response = client.get("/api/v1/sessions")
    assert sessions_response.status_code == 200, sessions_response.text
    assert payload["user_name"] in sessions_response.text


def test_login_rejects_bad_password(client: TestClient) -> None:
    payload = _unique_user_payload()
    _create_user(client, payload)

    response = client.post(
        "/api/v1/sessions/login",
        json={"user_name": payload["user_name"], "password": "wrong"},
    )

    assert response.status_code == 401, response.text


def test_protected_route_requires_authentication(client: TestClient) -> None:
    payload = _unique_user_payload()
    user_id = _create_user(client, payload)

    response = client.get(f"/api/v1/users/{user_id}")

    assert response.status_code == 401, response.text


def test_protected_route_rejects_missing_permission(client: TestClient) -> None:
    payload = _unique_user_payload()
    user_id = _create_user(client, payload)
    _login(client, payload)

    response = client.get(f"/api/v1/users/{user_id}")

    assert response.status_code == 403, response.text


def test_authenticated_logout_ends_session(client: TestClient) -> None:
    unauthenticated_response = client.get("/api/v1/sessions/logout")
    assert unauthenticated_response.status_code == 401, unauthenticated_response.text

    payload = _unique_user_payload()
    _create_user(client, payload)
    _login(client, payload)

    logout_response = client.get("/api/v1/sessions/logout")
    assert logout_response.status_code == 200, logout_response.text

    second_logout_response = client.get("/api/v1/sessions/logout")
    assert second_logout_response.status_code == 401, second_logout_response.text


def test_update_user(client: TestClient) -> None:
    payload = _unique_user_payload()
    user_id = _create_user(client, payload)
    _login(client, payload)
    _configure_permissions(
        client,
        user_id,
        [f"read/users/{user_id}", f"write/users/{user_id}"],
    )
    updated_email = f"updated_{uuid4().hex}@example.com"

    response = client.patch(
        f"/api/v1/users/{user_id}",
        json={"email": updated_email},
    )

    assert response.status_code == 200, response.text
    updated_user = response.json()
    assert updated_user["id"] == user_id
    assert updated_user["email"] == updated_email

    users_response = client.get("/api/v1/users")
    assert users_response.status_code == 200, users_response.text
    assert any(
        user["id"] == user_id and user["email"] == updated_email
        for user in users_response.json()
    )


def test_delete_user_and_sessions(client: TestClient) -> None:
    payload = _unique_user_payload()
    user_id = _create_user(client, payload)
    _configure_permissions(client, user_id, [f"delete/users/{user_id}"])
    _login(client, payload)

    response = client.delete(f"/api/v1/users/{user_id}")

    assert response.status_code == 200, response.text
    deleted_user = response.json()
    assert deleted_user["id"] == user_id

    # Deleting the user also deletes their sessions, so the current client
    # can no longer access protected user-list routes.
    users_response = client.get("/api/v1/users")
    assert users_response.status_code == 401, users_response.text

    sessions_response = client.get("/api/v1/sessions")
    assert sessions_response.status_code == 200, sessions_response.text
    assert payload["user_name"] not in sessions_response.text

    protected_response = client.get(f"/api/v1/users/{user_id}")
    assert protected_response.status_code == 401, protected_response.text
