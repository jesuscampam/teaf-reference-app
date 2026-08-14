"""End-to-end security checks, against the running server and browser.

Two kinds of assertion live here: what the API does to a request that
arrives without credentials, and what the browser is left holding. Both
are checked against the real thing — the API calls go out over HTTP to
the same uvicorn process the browser is talking to.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import DEMO_USER, WRONG_PASSWORD, create_task, sign_in

pytestmark = pytest.mark.e2e

#: Every task endpoint, with a valid body where one is required.
_TASK_CALLS = [
    ("GET", "/tasks", None),
    ("GET", "/tasks/stats", None),
    ("GET", "/tasks/00000000-0000-0000-0000-000000000000", None),
    ("POST", "/tasks", {"title": "t", "description": "d"}),
    ("PUT", "/tasks/00000000-0000-0000-0000-000000000000", {"title": "t", "description": "d"}),
    ("PATCH", "/tasks/00000000-0000-0000-0000-000000000000/status", {"status": "DONE"}),
    ("DELETE", "/tasks/00000000-0000-0000-0000-000000000000", None),
    ("POST", "/tasks/00000000-0000-0000-0000-000000000000/complete", None),
]


# -- The API, unauthenticated ------------------------------------------------------


@pytest.mark.parametrize(("method", "path", "body"), _TASK_CALLS)
def test_the_api_refuses_anonymous_requests(
    base_url: str, method: str, path: str, body: dict[str, str] | None
) -> None:
    with httpx.Client(base_url=base_url, timeout=10) as api:
        assert api.request(method, path, json=body).status_code == 401


def test_the_api_refuses_a_forged_token(base_url: str) -> None:
    with httpx.Client(base_url=base_url, timeout=10) as api:
        response = api.get("/tasks", headers={"Authorization": "Bearer forged.token.value"})

    assert response.status_code == 401


def test_a_revoked_token_stops_working(base_url: str) -> None:
    """Logout is server-side: the token itself dies, not just the copy in
    the browser."""
    with httpx.Client(base_url=base_url, timeout=10) as api:
        token = api.post(
            "/auth/login", json={"username": DEMO_USER[0], "password": DEMO_USER[1]}
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert api.get("/tasks", headers=headers).status_code == 200

        api.post("/auth/logout", headers=headers)

        assert api.get("/tasks", headers=headers).status_code == 401


def test_authentication_failures_expose_no_internals(base_url: str) -> None:
    with httpx.Client(base_url=base_url, timeout=10) as api:
        anonymous = api.get("/tasks").text.lower()
        bad_login = api.post(
            "/auth/login", json={"username": "nobody", "password": WRONG_PASSWORD}
        ).text.lower()

    for body in (anonymous, bad_login):
        for leak in ("traceback", 'file "', "/home/", "sqlite", "argon2", "secret", "jwt_secret"):
            assert leak not in body, leak


def test_the_password_is_never_echoed_back(base_url: str) -> None:
    with httpx.Client(base_url=base_url, timeout=10) as api:
        response = api.post(
            "/auth/login", json={"username": DEMO_USER[0], "password": WRONG_PASSWORD}
        )

    assert WRONG_PASSWORD not in response.text


# -- The browser -------------------------------------------------------------------


def test_the_password_is_not_left_in_the_dom(page: Page) -> None:
    sign_in(page)

    assert DEMO_USER[1] not in page.content()


def test_the_token_is_not_rendered_anywhere(page: Page) -> None:
    """The session is in storage, which is expected; it must not also be
    printed into the page where a screenshot would capture it."""
    sign_in(page)
    create_task(page, "Anything")

    token = page.evaluate("JSON.parse(sessionStorage.getItem('teaf.session')).accessToken")
    assert token
    assert token not in page.content()


def test_no_credentials_travel_in_the_url(page: Page) -> None:
    sign_in(page)

    assert DEMO_USER[1] not in page.url
    assert "token" not in page.url.lower()


def test_the_password_field_is_masked(page: Page) -> None:
    page.goto("/login")

    expect(page.locator("#password")).to_have_attribute("type", "password")


def test_logout_leaves_nothing_behind(page: Page) -> None:
    sign_in(page)

    page.click("#logout-button")
    page.wait_for_url("**/login")

    assert page.evaluate("sessionStorage.getItem('teaf.session')") is None
    assert page.evaluate("localStorage.length") == 0


def test_the_session_does_not_outlive_the_tab(page: Page) -> None:
    """`sessionStorage`, not `localStorage`: a new context starts signed
    out even though the old one never logged out. See session.js for the
    storage trade-off."""
    sign_in(page)

    browser = page.context.browser
    assert browser is not None  # a page from a live context always has one
    fresh = browser.new_context(base_url=page.url.rsplit("/", 1)[0])
    try:
        other_tab = fresh.new_page()
        other_tab.goto("/")
        other_tab.wait_for_url("**/login")
        expect(other_tab.locator("#login-form")).to_be_visible()
    finally:
        fresh.close()


def test_the_page_reports_no_console_errors(page: Page) -> None:
    """A CSP violation or a broken module shows up here and nowhere else."""
    errors: list[str] = []
    page.on(
        "console",
        lambda message: errors.append(message.text) if message.type == "error" else None,
    )

    sign_in(page)
    create_task(page, "Console check")
    page.click("#logout-button")
    page.wait_for_url("**/login")

    # The browser requests /favicon.ico on its own; a 404 for it says
    # nothing about this application.
    assert [error for error in errors if "favicon" not in error.lower()] == []
