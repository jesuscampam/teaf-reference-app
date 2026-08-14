"""Tests for the Task Manager UI (app/static/), served at GET / and /static/*."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import _route_index


def test_root_serves_html_ui(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "TEAF Task Manager" in response.text


def test_root_csp_allows_same_origin_assets(client: TestClient) -> None:
    """TEAF's default CSP (`default-src 'none'`) blocks the UI's own CSS/JS/fetch
    calls in a real browser (curl doesn't enforce CSP, so this only surfaces
    there) — see app/main.py for the sanctioned, public override."""
    response = client.get("/")

    csp = response.headers["content-security-policy"]
    assert csp == "default-src 'self'; frame-ancestors 'none'"


def test_static_stylesheet_is_served(client: TestClient) -> None:
    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_static_script_is_served(client: TestClient) -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200


def test_health_and_info_still_json_after_root_reorder(client: TestClient) -> None:
    """Reordering the "/" route (see app/main.py) must not disturb any other route."""
    health = client.get("/health")
    info = client.get("/info")

    assert health.headers["content-type"].startswith("application/json")
    assert info.headers["content-type"].startswith("application/json")


def test_login_page_is_served(client: TestClient) -> None:
    """`/login` is public — it has to be, or nobody could ever sign in."""
    response = client.get("/login")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sign in" in response.text


def test_login_page_carries_the_same_csp_override(client: TestClient) -> None:
    csp = client.get("/login").headers["content-security-policy"]

    assert csp == "default-src 'self'; frame-ancestors 'none'"


def test_login_page_does_not_contain_a_password(client: TestClient) -> None:
    """The demo hint names the accounts, which is intended; make sure the
    page never carries anything resembling a real secret."""
    body = client.get("/login").text.lower()

    assert "jwt" not in body
    assert "secret" not in body


def test_the_session_script_is_served(client: TestClient) -> None:
    assert client.get("/static/session.js").status_code == 200
    assert client.get("/static/login.js").status_code == 200


def test_route_lookup_fails_loudly_for_an_unknown_endpoint() -> None:
    """`_route_index` orders the UI route ahead of TEAF's own `/`. If it
    ever cannot find the route, it must say so rather than silently
    reordering the wrong one."""
    with pytest.raises(RuntimeError, match="UI route not found"):
        _route_index(lambda: None)
