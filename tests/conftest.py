"""Shared fixtures for tests that exercise the real, wired `app.main.app`.

Entering `TestClient(app)` as a context manager runs TEAF's ASGI lifespan
(`Runtime.startup()` + module bootstrap). `app.main.app` is a
process-wide singleton (the module is only ever imported once), and
re-entering the lifespan a second time on the same `Runtime` re-registers
`TaskModule` and raises `ModuleRegistrationException` ("already
registered") — so this fixture is session-scoped: the lifespan starts
once, is shared by every test file that needs a live client, and shuts
down once when the whole test session ends.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
