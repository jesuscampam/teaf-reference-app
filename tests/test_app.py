"""Tests for backend.app — the reference TEAF consumption pattern.

These tests are guarded by `pytest.importorskip("teaf")` because TEAF
does not currently expose a public `teaf` package (see
docs/BOOTSTRAP.md, "TEAF Public API Limitation"). They SKIP cleanly
today rather than fail, and will activate automatically the moment
`teaf` becomes importable — no changes needed here.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "teaf",
    reason="TEAF does not yet expose a public `teaf` package — see docs/BOOTSTRAP.md.",
)

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import app  # noqa: E402

client = TestClient(app)


def test_application_instantiates() -> None:
    assert app is not None


@pytest.mark.parametrize("path", ["/", "/health", "/info", "/runtime/info"])
def test_endpoint_responds(path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
