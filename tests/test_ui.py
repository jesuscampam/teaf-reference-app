"""Tests for the Task Manager UI (app/static/), served at GET / and /static/*."""

from __future__ import annotations

from fastapi.testclient import TestClient


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
