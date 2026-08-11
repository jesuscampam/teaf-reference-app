"""Shared fixtures for tests that exercise the real, wired `app.main.app`.

Entering `TestClient(app)` as a context manager runs TEAF's ASGI lifespan
(`Runtime.startup()` + module bootstrap). `app.main.app` is a
process-wide singleton (the module is only ever imported once), and
re-entering the lifespan a second time on the same `Runtime` re-registers
`TaskModule` and raises `ModuleRegistrationException` ("already
registered") — so this fixture is session-scoped: the lifespan starts
once, is shared by every test file that needs a live client, and shuts
down once when the whole test session ends.

The environment variable below must be set **before** `app.main` is
imported: importing it constructs `TaskModule()`, which reads
`task_database_path` from settings and would otherwise write a real
`tasks.db` into the working directory during a test run. `:memory:`
gives each test session a database that never touches disk; the
persistence-across-restart behaviour is covered explicitly, against a
real file, in tests/modules/task/test_repository.py.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

os.environ.setdefault("TASK_DATABASE_PATH", ":memory:")

import pytest  # noqa: E402 — must follow the env var set above
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_tasks(request: pytest.FixtureRequest) -> None:
    """Start every client-using test against an empty task list.

    The application (and therefore its repository) is shared for the whole
    session, so without this a task created by one test would still be
    there for the next. Deleting through the API keeps the fixture honest:
    it uses the same path a client would.

    Guarded on `client` actually being requested so the pure unit tests
    (models, services, repository) don't drag a live `Application` into
    scope just by existing.
    """
    if "client" not in request.fixturenames:
        return
    live_client: TestClient = request.getfixturevalue("client")
    for task in live_client.get("/tasks").json():
        live_client.delete(f"/tasks/{task['id']}")
