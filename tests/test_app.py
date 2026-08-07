"""Tests for app.main — the reference TEAF consumption pattern.

`Application` is instantiated (`from teaf import Application`) and served
through `TestClient` exactly as any ASGI app would be. Uses the shared
session-scoped `client` fixture (tests/conftest.py) — see its docstring
for why a fresh `TestClient(app)` per test file isn't safe here.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_application_instantiates() -> None:
    assert app is not None


@pytest.mark.parametrize("path", ["/", "/health", "/info", "/runtime/info"])
def test_endpoint_responds(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
