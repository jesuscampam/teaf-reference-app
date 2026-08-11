"""Tests for app.modules.task.routes — plain FastAPI, isolated from TEAF.

The router is mounted on a bare `FastAPI()` here rather than on the real
`Application`, so a failure points at the HTTP layer and nothing else.
Full-stack behaviour is covered in test_integration.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.task.repository import InMemoryTaskRepository
from app.modules.task.routes import create_task_router
from app.modules.task.services import TaskService


@pytest.fixture
def client() -> Iterator[TestClient]:
    service = TaskService(InMemoryTaskRepository())
    app = FastAPI()
    app.include_router(create_task_router(lambda: service))
    with TestClient(app) as test_client:
        yield test_client


def _create(client: TestClient, title: str = "a", description: str = "b") -> dict[str, str]:
    response = client.post("/tasks", json={"title": title, "description": description})
    assert response.status_code == 201
    created: dict[str, str] = response.json()
    return created


# -- Reads ---------------------------------------------------------------------


def test_create_and_list(client: TestClient) -> None:
    created = _create(client)

    listed = client.get("/tasks")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created["id"]


def test_list_is_empty_initially(client: TestClient) -> None:
    assert client.get("/tasks").json() == []


def test_new_task_starts_in_todo(client: TestClient) -> None:
    assert _create(client)["status"] == "TODO"


def test_get_missing_returns_404(client: TestClient) -> None:
    response = client.get(f"/tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_get_with_a_malformed_id_returns_422(client: TestClient) -> None:
    assert client.get("/tasks/not-a-uuid").status_code == 422


# -- Writes --------------------------------------------------------------------


def test_update(client: TestClient) -> None:
    created = _create(client)

    response = client.put(f"/tasks/{created['id']}", json={"title": "c", "description": "d"})

    assert response.status_code == 200
    assert response.json()["title"] == "c"


def test_update_missing_returns_404(client: TestClient) -> None:
    response = client.put(f"/tasks/{uuid4()}", json={"title": "c", "description": "d"})

    assert response.status_code == 404


def test_delete(client: TestClient) -> None:
    created = _create(client)

    response = client.delete(f"/tasks/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_missing_returns_404(client: TestClient) -> None:
    assert client.delete(f"/tasks/{uuid4()}").status_code == 404


# -- Status --------------------------------------------------------------------


@pytest.mark.parametrize("target", ["IN_PROGRESS", "DONE"])
def test_patch_status(client: TestClient, target: str) -> None:
    created = _create(client)

    response = client.patch(f"/tasks/{created['id']}/status", json={"status": target})

    assert response.status_code == 200
    assert response.json()["status"] == target


def test_patch_status_missing_returns_404(client: TestClient) -> None:
    response = client.patch(f"/tasks/{uuid4()}/status", json={"status": "DONE"})

    assert response.status_code == 404


def test_patch_status_to_current_status_returns_409(client: TestClient) -> None:
    created = _create(client)

    response = client.patch(f"/tasks/{created['id']}/status", json={"status": "TODO"})

    assert response.status_code == 409
    assert "already" in response.json()["detail"]


def test_patch_status_rejects_an_unknown_status(client: TestClient) -> None:
    created = _create(client)

    response = client.patch(f"/tasks/{created['id']}/status", json={"status": "ARCHIVED"})

    assert response.status_code == 422


def test_complete(client: TestClient) -> None:
    created = _create(client)

    response = client.post(f"/tasks/{created['id']}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "DONE"


def test_complete_missing_returns_404(client: TestClient) -> None:
    assert client.post(f"/tasks/{uuid4()}/complete").status_code == 404


def test_complete_twice_returns_409(client: TestClient) -> None:
    created = _create(client)
    client.post(f"/tasks/{created['id']}/complete")

    assert client.post(f"/tasks/{created['id']}/complete").status_code == 409


# -- Validation ----------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "", "description": "b"},
        {"title": "a", "description": ""},
        {"title": "x" * 201, "description": "b"},
        {"description": "missing title"},
        {"title": "missing description"},
    ],
)
def test_create_rejects_invalid_payloads(client: TestClient, payload: dict[str, str]) -> None:
    assert client.post("/tasks", json=payload).status_code == 422


def test_whitespace_only_title_is_rejected_by_the_service(client: TestClient) -> None:
    """Passes the schema's `min_length` but not the domain rule — 400, not 422."""
    response = client.post("/tasks", json={"title": "   ", "description": "b"})

    assert response.status_code == 400
    assert "blank" in response.json()["detail"]


def test_update_with_a_whitespace_only_title_returns_400(client: TestClient) -> None:
    """Same split as on create: the schema accepts it, the domain rule doesn't."""
    created = _create(client)

    response = client.put(f"/tasks/{created['id']}", json={"title": " ", "description": "ok"})

    assert response.status_code == 400
    assert "blank" in response.json()["detail"]


def test_errors_never_leak_internals(client: TestClient) -> None:
    body = client.get(f"/tasks/{uuid4()}").json()

    assert set(body) == {"detail"}
    assert "Traceback" not in body["detail"]


# -- Stats ---------------------------------------------------------------------


def test_stats_on_an_empty_list(client: TestClient) -> None:
    assert client.get("/tasks/stats").json() == {
        "total": 0,
        "todo": 0,
        "in_progress": 0,
        "done": 0,
    }


def test_stats_count_each_status(client: TestClient) -> None:
    _create(client, title="stays todo")
    started = _create(client, title="started")
    finished = _create(client, title="finished")
    client.patch(f"/tasks/{started['id']}/status", json={"status": "IN_PROGRESS"})
    client.post(f"/tasks/{finished['id']}/complete")

    assert client.get("/tasks/stats").json() == {
        "total": 3,
        "todo": 1,
        "in_progress": 1,
        "done": 1,
    }


def test_stats_path_is_not_parsed_as_a_task_id(client: TestClient) -> None:
    """Route ordering regression guard: `/tasks/stats` must not hit `/tasks/{id}`."""
    assert client.get("/tasks/stats").status_code == 200
