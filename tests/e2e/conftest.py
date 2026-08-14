"""Fixtures for the browser end-to-end tests.

These are the only tests that run the application the way a user meets
it: a real `uvicorn` process, a real browser, the real static files, the
real HTTP client, real TEAF middleware, real JWTs, and a real SQLite
file. Nothing is stubbed, and nothing is called directly — every
assertion goes through the UI.

Isolation comes from a per-session temporary database and a random free
port, so a run never touches a developer's `tasks.db` and never collides
with an app already running on 8000.

If Playwright or its browser binary is missing, the whole package skips
rather than failing: the browser is not a pip dependency, and a machine
without one should still be able to run every other test.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="playwright is not installed")

from playwright.sync_api import Browser, Page, sync_playwright  # noqa: E402

#: Where this environment keeps its browsers. Playwright normally resolves
#: this itself; the explicit path covers images that ship Chromium under a
#: fixed location without the matching driver registry.
_CHROMIUM_CANDIDATES = (
    Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome"),
    Path("/opt/pw-browsers/chromium/chrome-linux/chrome"),
)

#: Demo credentials, as the login page advertises them. Duplicated here on
#: purpose: an E2E test should type what a user would type, not import the
#: application's own settings.
DEMO_USER = ("demo", "demo1234")
DEMO_VIEWER = ("viewer", "viewer1234")
WRONG_PASSWORD = "definitely-not-the-password"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def _chromium_executable() -> str | None:
    for candidate in _CHROMIUM_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return None


@pytest.fixture(scope="session")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """A real `uvicorn` process, on its own port, with its own database."""
    port = _free_port()
    database = tmp_path_factory.mktemp("e2e") / "tasks.db"

    environment = {
        **os.environ,
        "TASK_DATABASE_PATH": str(database),
        # Fixed so tokens are reproducible within the run. It signs for a
        # server that exists for the duration of this test session only.
        "AUTH_JWT_SECRET": "e2e-only-signing-key-not-a-secret-32bytes",
        # TEAF validates this against its own enum; "test" is not one of
        # its values (development / testing / staging / production).
        "ENVIRONMENT": "testing",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_serving(process, url)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _wait_until_serving(process: subprocess.Popen[str], url: str, timeout: float = 30.0) -> None:
    """Poll the port until the server answers, or fail with its output.

    Raising with the captured stdout matters: a server that died on
    startup would otherwise show up as an opaque connection timeout.
    """
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"uvicorn exited before serving:\n{output}")
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1):
                return
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    process.terminate()
    raise RuntimeError(f"uvicorn did not start within {timeout}s")


@pytest.fixture(autouse=True)
def clean_database(base_url: str) -> None:
    """Empty the task list before every E2E test.

    The server and its SQLite file are shared for the whole session (a
    restart per test would cost seconds each), so without this a task
    created by one test would still be on screen for the next — and the
    counter assertions would depend on execution order.

    This runs over HTTP rather than through the UI on purpose: it is
    setup, not the behaviour under test, and driving the browser to
    delete leftovers would be slow and would obscure what each test is
    actually exercising.
    """
    import httpx

    with httpx.Client(base_url=base_url, timeout=10) as api:
        token = api.post(
            "/auth/login", json={"username": DEMO_USER[0], "password": DEMO_USER[1]}
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        for task in api.get("/tasks", headers=headers).json():
            api.delete(f"/tasks/{task['id']}", headers=headers)


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    executable = _chromium_executable()
    with sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch(executable_path=executable)
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"Chromium is not available: {exc}")
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def page(browser: Browser, base_url: str) -> Iterator[Page]:
    """A fresh browser context per test.

    A new context means empty `sessionStorage`, so no test inherits
    another's login — the same guarantee a new browser window gives a
    user.
    """
    context = browser.new_context(base_url=base_url)
    new_page = context.new_page()
    try:
        yield new_page
    finally:
        context.close()


def sign_in(page: Page, credentials: tuple[str, str] = DEMO_USER) -> None:
    """Log in through the form, exactly as a user does.

    Waits for the username to appear rather than for `#task-list`: the
    list element is in the static HTML and exists before any script runs,
    so waiting on it would return while the app was still starting up —
    before `/auth/me` had resolved and before permission-dependent parts
    of the page (the create form) had settled.
    """
    username, password = credentials
    page.goto("/login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#login-submit")
    page.wait_for_selector(f"#session-username:text-is('{username}')")


def create_task(page: Page, title: str, description: str = "created by an e2e test") -> None:
    page.fill("#create-title", title)
    page.fill("#create-description", description)
    page.click("#create-form button[type=submit]")
    page.wait_for_selector(f".task-title:text-is('{title}')")
