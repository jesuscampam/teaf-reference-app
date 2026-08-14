"""HTTP-level tests for the `/auth` endpoints, against the real Application.

These run against `app.main.app` rather than an isolated router because
the behaviour under test — `401` bodies, `@authorize()` on `/auth/logout`
and `/auth/me` — depends on middleware that TEAF's `create_app()`
installs. See the note in tests/modules/task/test_routes.py.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import DEMO_USER, DEMO_VIEWER, bearer, login

# -- Login -----------------------------------------------------------------------


def test_login_succeeds_with_demo_credentials(client: TestClient) -> None:
    username, password = DEMO_USER

    response = client.post("/auth/login", json={"username": username, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == username
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_reports_roles_and_permissions(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": DEMO_USER[0], "password": DEMO_USER[1]})

    body = response.json()
    assert body["roles"] == ["user"]
    assert body["permissions"] == ["task.read", "task.write"]


def test_viewer_login_reports_only_read(client: TestClient) -> None:
    response = client.post(
        "/auth/login", json={"username": DEMO_VIEWER[0], "password": DEMO_VIEWER[1]}
    )

    assert response.json()["permissions"] == ["task.read"]


def test_login_with_a_wrong_password_returns_401(client: TestClient) -> None:
    response = client.post(
        "/auth/login", json={"username": DEMO_USER[0], "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_with_an_unknown_user_returns_401(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "nobody", "password": "whatever"})

    assert response.status_code == 401


def test_both_login_failures_look_identical(client: TestClient) -> None:
    """A wrong password and an unknown user must be indistinguishable, or
    the response becomes an oracle for which usernames exist.

    `correlationId` is excluded: TEAF mints a fresh one per request, so it
    differs between any two calls and carries nothing about the account.
    """
    wrong_password = client.post(
        "/auth/login", json={"username": DEMO_USER[0], "password": "wrong-password"}
    )
    unknown_user = client.post(
        "/auth/login", json={"username": "nobody", "password": "wrong-password"}
    )

    assert wrong_password.status_code == unknown_user.status_code
    assert _without_correlation_id(wrong_password.json()) == _without_correlation_id(
        unknown_user.json()
    )


def _without_correlation_id(body: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in body.items() if key != "correlationId"}


def test_failed_login_never_returns_a_token(client: TestClient) -> None:
    response = client.post(
        "/auth/login", json={"username": DEMO_USER[0], "password": "wrong-password"}
    )

    assert "access_token" not in response.text


def test_failed_login_does_not_echo_the_password(client: TestClient) -> None:
    secret = "a-very-distinctive-wrong-password"

    response = client.post("/auth/login", json={"username": DEMO_USER[0], "password": secret})

    assert secret not in response.text


def test_login_rejects_a_malformed_payload(client: TestClient) -> None:
    assert client.post("/auth/login", json={"username": "only"}).status_code == 422
    assert client.post("/auth/login", json={}).status_code == 422


def test_login_error_body_exposes_no_internals(client: TestClient) -> None:
    body = client.post(
        "/auth/login", json={"username": "nobody", "password": "whatever"}
    ).text.lower()

    for leak in ("traceback", "/home/", "argon2", "sqlite", "secret", "hash"):
        assert leak not in body, leak


# -- Session (`/auth/me`) ---------------------------------------------------------


def test_me_requires_a_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_describes_the_current_session(client: TestClient) -> None:
    headers = bearer(login(client, DEMO_USER))

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "username": DEMO_USER[0],
        "roles": ["user"],
        "permissions": ["task.read", "task.write"],
    }


def test_me_never_returns_the_token_itself(client: TestClient) -> None:
    token = login(client, DEMO_USER)

    response = client.get("/auth/me", headers=bearer(token))

    assert token not in response.text


# -- Logout ------------------------------------------------------------------------


def test_logout_requires_a_token(client: TestClient) -> None:
    assert client.post("/auth/logout").status_code == 401


def test_logout_succeeds_and_invalidates_the_token(client: TestClient) -> None:
    """The token stops working against the API, not just in the browser."""
    headers = bearer(login(client, DEMO_USER))
    assert client.get("/tasks", headers=headers).status_code == 200

    assert client.post("/auth/logout", headers=headers).status_code == 204

    assert client.get("/tasks", headers=headers).status_code == 401
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_logout_leaves_other_sessions_alone(client: TestClient) -> None:
    first = bearer(login(client, DEMO_USER))
    second = bearer(login(client, DEMO_USER))

    client.post("/auth/logout", headers=first)

    assert client.get("/tasks", headers=second).status_code == 200


def test_a_new_login_works_after_logout(client: TestClient) -> None:
    headers = bearer(login(client, DEMO_USER))
    client.post("/auth/logout", headers=headers)

    assert client.get("/tasks", headers=bearer(login(client, DEMO_USER))).status_code == 200


# -- Registration with the runtime --------------------------------------------------


def test_auth_module_is_registered(client: TestClient) -> None:
    modules = {module["id"] for module in client.get("/runtime/modules").json()}

    assert "auth" in modules


def test_auth_capability_is_registered(client: TestClient) -> None:
    capabilities = {c["id"] for c in client.get("/runtime/capabilities").json()}

    assert "auth.demo-login" in capabilities


def test_auth_health_check_is_reported(client: TestClient) -> None:
    checks = client.get("/health").json()["modules"]["checks"]

    assert checks["auth.auth.ping"] == "healthy"
