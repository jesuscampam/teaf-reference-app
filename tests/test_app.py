"""Tests for app.main — the reference TEAF consumption pattern.

TEAF v0.6.1-alpha ships a real, installable `teaf` package, so these run
for real (no skip guard): `Application` is instantiated and served
through `TestClient` exactly as any ASGI app would be.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_application_instantiates() -> None:
    assert app is not None


@pytest.mark.parametrize("path", ["/", "/health", "/info", "/runtime/info"])
def test_endpoint_responds(path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
