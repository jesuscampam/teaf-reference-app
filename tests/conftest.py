"""Shared fixtures for tests that exercise the real, wired `app.main.app`.

Entering `TestClient(app)` as a context manager runs TEAF's ASGI lifespan
(`Runtime.startup()` + module bootstrap). `app.main.app` is a
process-wide singleton (the module is only ever imported once), and
re-entering the lifespan a second time on the same `Runtime` re-registers
the modules and raises `ModuleRegistrationException` ("already
registered") — so the client fixture is session-scoped: the lifespan
starts once, is shared by every test file that needs a live client, and
shuts down once when the whole test session ends.

The environment variables below must be set **before** `app.main` is
imported: importing it constructs the modules, which read settings.
`TASK_DATABASE_PATH=:memory:` keeps the test run off disk (persistence
against a real file is covered explicitly in
tests/modules/task/test_repository.py), and a fixed `AUTH_JWT_SECRET`
makes token behaviour reproducible instead of depending on the random
per-process key the application generates by default. It is a test key
and grants nothing: the app it signs for exists only inside this process.

Since Sprint A3 every `/tasks` endpoint requires a token, so `client` is
now an *unauthenticated* client. Use `user_client` for the read/write
account, `viewer_client` for the read-only one, and `auth_headers` when a
test needs the raw header.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

os.environ.setdefault("TASK_DATABASE_PATH", ":memory:")
os.environ.setdefault("AUTH_JWT_SECRET", "test-only-signing-key-not-a-secret-32b+")

import pytest  # noqa: E402 — must follow the env vars set above
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

#: Credentials of the two demo accounts, read from the same settings the
#: application uses rather than repeated as literals here.
DEMO_USER = (get_settings().auth_demo_username, get_settings().auth_demo_password)
DEMO_VIEWER = (get_settings().auth_viewer_username, get_settings().auth_viewer_password)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Run `async def` tests on asyncio via the anyio plugin.

    anyio ships with the dependency tree already (Starlette needs it), so
    async tests cost no new dependency. Modules with async tests opt in
    with `pytestmark = pytest.mark.anyio`.
    """
    return "asyncio"


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """A client with no credentials. Every `/tasks` call answers 401."""
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, credentials: tuple[str, str]) -> str:
    """Log in through the real endpoint and return the access token."""
    username, password = credentials
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Authorization header for the read/write demo account."""
    return bearer(login(client, DEMO_USER))


def _clear_tasks(client: TestClient, headers: dict[str, str]) -> None:
    """Empty the task list through the API, with a real token.

    The application (and therefore its repository) is shared for the whole
    session, so without this a task created by one test would still be
    there for the next. Cleaning through HTTP keeps the helper honest: it
    uses the same path a client would.
    """
    for task in client.get("/tasks", headers=headers).json():
        client.delete(f"/tasks/{task['id']}", headers=headers)


@pytest.fixture
def user_client(client: TestClient, auth_headers: dict[str, str]) -> Iterator[TestClient]:
    """The read/write account, with its token attached to every request.

    The header is set on the shared client and removed afterwards rather
    than building a second `TestClient`, because a second client would
    re-enter the ASGI lifespan — see this module's docstring.

    Cleanup lives here rather than in an autouse fixture so it only runs
    for tests that actually touch the shared application: the isolated
    routers in tests/modules/*/test_routes.py build their own app with no
    `/auth` endpoints to log in against.
    """
    _clear_tasks(client, auth_headers)
    client.headers.update(auth_headers)
    try:
        yield client
    finally:
        client.headers.pop("Authorization", None)


@pytest.fixture
def viewer_client(client: TestClient) -> Iterator[TestClient]:
    """The read-only account. Mutating endpoints answer 403 for it."""
    headers = bearer(login(client, DEMO_VIEWER))
    _clear_tasks(client, bearer(login(client, DEMO_USER)))
    client.headers.update(headers)
    try:
        yield client
    finally:
        client.headers.pop("Authorization", None)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Run the browser end-to-end tests last.

    Playwright's synchronous API installs an event loop that stays alive
    for the rest of the session. Any async test collected after it fails
    with "Cannot run the event loop while another loop is running" — not
    because the test is wrong, but because Playwright got there first.
    Collection order is alphabetical, which puts `tests/e2e` ahead of
    `tests/modules`, so the order is fixed here rather than left to a
    directory name.

    Sorting beats splitting the suite into two commands: one `pytest`
    still runs everything, and nothing has to be remembered.
    """
    items.sort(key=lambda item: "tests/e2e" in str(item.path).replace("\\", "/"))
