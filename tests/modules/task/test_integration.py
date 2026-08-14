"""Integration tests: the Task module registered against the real Application.

Uses the shared session-scoped `client` fixture (tests/conftest.py) —
same `app.main.app` singleton `uvicorn app.main:app` serves, so these
exercise the actual module-registration wiring, not a reconstruction of
it. The full path is covered end to end here:

    HTTP -> routes -> TaskService -> SqliteTaskRepository -> back out
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from teaf import EventBus

from app.main import app
from app.modules.task.events import TASK_EVENT_NAMES
from app.modules.task.repository import SqliteTaskRepository
from app.modules.task.services import TaskService
from tests.conftest import DEMO_VIEWER, bearer, login

# -- Registration --------------------------------------------------------------


def test_task_module_appears_in_runtime_info(client: TestClient) -> None:
    response = client.get("/runtime/info")

    assert response.status_code == 200
    assert response.json()["registeredModules"] >= 6  # TEAF built-ins + task


def test_task_module_appears_in_runtime_modules(client: TestClient) -> None:
    response = client.get("/runtime/modules")

    assert response.status_code == 200
    assert "task" in {module["id"] for module in response.json()}


def test_task_capability_registered(client: TestClient) -> None:
    response = client.get("/runtime/capabilities")

    assert response.status_code == 200
    assert "task.manage" in {capability["id"] for capability in response.json()}


def test_task_health_check_is_reported(client: TestClient) -> None:
    checks = client.get("/health").json()["modules"]["checks"]

    assert checks["task.task.ping"] == "healthy"


# -- The full demonstration flow ------------------------------------------------


def test_task_endpoints_work_through_real_app(user_client: TestClient) -> None:
    created = user_client.post("/tasks", json={"title": "Integration", "description": "test"})
    assert created.status_code == 201

    task_id = created.json()["id"]
    assert user_client.get(f"/tasks/{task_id}").status_code == 200

    started = user_client.patch(f"/tasks/{task_id}/status", json={"status": "IN_PROGRESS"})
    assert started.json()["status"] == "IN_PROGRESS"

    completed = user_client.post(f"/tasks/{task_id}/complete")
    assert completed.json()["status"] == "DONE"

    assert user_client.delete(f"/tasks/{task_id}").status_code == 204
    assert user_client.get(f"/tasks/{task_id}").status_code == 404


def test_stats_reflect_real_persisted_tasks(user_client: TestClient) -> None:
    """The dashboard numbers come from stored data, never from a counter
    the UI keeps on the side."""
    user_client.post("/tasks", json={"title": "one", "description": "d"})
    second = user_client.post("/tasks", json={"title": "two", "description": "d"}).json()
    user_client.patch(f"/tasks/{second['id']}/status", json={"status": "DONE"})

    assert user_client.get("/tasks/stats").json() == {
        "total": 2,
        "todo": 1,
        "in_progress": 0,
        "done": 1,
    }


def test_events_reach_the_applications_own_runtime_bus(user_client: TestClient) -> None:
    """An HTTP request ends up publishing an application event on the
    framework's bus. TEAF interleaves its own events (`service.resolved`
    fires on every route call), so only the application's are compared.
    """
    bus = app.runtime.event_bus
    assert isinstance(bus, EventBus)
    before = len(bus.history())

    created = user_client.post("/tasks", json={"title": "observed", "description": "d"}).json()
    user_client.patch(f"/tasks/{created['id']}/status", json={"status": "DONE"})

    names = [event.name for event in bus.history()[before:] if event.name in TASK_EVENT_NAMES]
    assert names == ["task.created", "task.status_changed"]


def test_concurrent_requests_all_succeed(user_client: TestClient) -> None:
    """The UI loads the list and the counts in parallel on every render.

    Starlette runs sync handlers in a thread pool, so those two land on
    different threads. This is the shape of request that surfaced a false
    `CircularDependencyException` from TEAF's container before the module
    started resolving its services during bootstrap.
    """
    user_client.post("/tasks", json={"title": "concurrent", "description": "d"})
    paths = ["/tasks", "/tasks/stats"] * 10

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = [response.status_code for response in pool.map(user_client.get, paths)]

    assert codes == [200] * len(paths)


# -- Persistence across a restart ------------------------------------------------


def test_tasks_survive_an_application_restart(tmp_path: Path) -> None:
    """The demonstration scenario's last step, proven without a live server.

    A second repository over the same file is what the application gets
    after a restart: new object, new connection, same database. Exercised
    through `TaskService` so the whole stack above the connection is in
    play, not just the SQL.
    """
    database = tmp_path / "restart.db"

    with SqliteTaskRepository(database) as before_restart:
        created = TaskService(before_restart).create_task(
            title="Survivor", description="written before the restart"
        )

    with SqliteTaskRepository(database) as after_restart:
        second_run = TaskService(after_restart)
        restored = second_run.get_task(created.id)
        surviving_ids = [task.id for task in second_run.list_tasks()]

    assert restored.title == "Survivor"
    assert surviving_ids == [created.id]


# -- Authentication and authorization, against the real Application --------------
#
# This is where the HTTP status codes are asserted. TEAF maps its own
# authentication/authorization exceptions to 401/403 in middleware that
# `create_app()` installs, so those codes only exist inside a real
# `Application` — see the note in test_routes.py.

_Call = tuple[str, str, dict[str, str] | None]

_READ_CALLS: list[_Call] = [
    ("get", "/tasks", None),
    ("get", "/tasks/stats", None),
    ("get", f"/tasks/{uuid4()}", None),
]
_WRITE_CALLS: list[_Call] = [
    ("post", "/tasks", {"title": "t", "description": "d"}),
    ("put", f"/tasks/{uuid4()}", {"title": "t", "description": "d"}),
    ("patch", f"/tasks/{uuid4()}/status", {"status": "DONE"}),
    ("delete", f"/tasks/{uuid4()}", None),
    ("post", f"/tasks/{uuid4()}/complete", None),
]


@pytest.mark.parametrize(("method", "path", "body"), _READ_CALLS + _WRITE_CALLS)
def test_every_task_endpoint_returns_401_without_a_token(
    client: TestClient, method: str, path: str, body: dict[str, str] | None
) -> None:
    assert client.request(method, path, json=body).status_code == 401


@pytest.mark.parametrize("header", ["Bearer not-a-jwt", "Bearer ", "Basic dXNlcjpwYXNz", ""])
def test_malformed_credentials_return_401(client: TestClient, header: str) -> None:
    response = client.get("/tasks", headers={"Authorization": header})

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), _WRITE_CALLS)
def test_write_endpoints_return_403_for_a_read_only_account(
    viewer_client: TestClient, method: str, path: str, body: dict[str, str] | None
) -> None:
    """Authenticated but not permitted — 403, and distinct from the 401
    an anonymous caller gets. The distinction is the point: it tells a
    client whether to re-authenticate or to stop asking."""
    assert viewer_client.request(method, path, json=body).status_code == 403


@pytest.mark.parametrize(("method", "path", "body"), _READ_CALLS)
def test_read_endpoints_work_for_a_read_only_account(
    viewer_client: TestClient, method: str, path: str, body: dict[str, str] | None
) -> None:
    assert viewer_client.request(method, path, json=body).status_code in {200, 404}


def test_a_viewer_cannot_change_data_even_when_the_task_exists(
    user_client: TestClient, client: TestClient
) -> None:
    """403 is refusal, not a 404 in disguise: the task is really there."""
    created = user_client.post("/tasks", json={"title": "guarded", "description": "d"}).json()
    client.headers.pop("Authorization", None)
    viewer = bearer(login(client, DEMO_VIEWER))

    assert client.get(f"/tasks/{created['id']}", headers=viewer).status_code == 200
    assert client.delete(f"/tasks/{created['id']}", headers=viewer).status_code == 403
    assert client.get(f"/tasks/{created['id']}", headers=viewer).status_code == 200


def test_teaf_own_endpoints_stay_public(client: TestClient) -> None:
    """Health and runtime introspection are not behind the app's login —
    protecting them was never in scope, and a monitor needs `/health`."""
    for path in ("/health", "/info", "/runtime/info", "/runtime/modules"):
        assert client.get(path).status_code == 200, path
