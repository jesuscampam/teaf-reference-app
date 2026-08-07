"""Tests for app.modules.task.routes — plain FastAPI, isolated from TEAF."""

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


def test_create_and_list(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "a", "description": "b"})
    assert created.status_code == 201

    listed = client.get("/tasks")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created.json()["id"]


def test_get_missing_returns_404(client: TestClient) -> None:
    response = client.get(f"/tasks/{uuid4()}")

    assert response.status_code == 404


def test_update(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "a", "description": "b"}).json()

    response = client.put(f"/tasks/{created['id']}", json={"title": "c", "description": "d"})

    assert response.status_code == 200
    assert response.json()["title"] == "c"


def test_update_missing_returns_404(client: TestClient) -> None:
    response = client.put(f"/tasks/{uuid4()}", json={"title": "c", "description": "d"})

    assert response.status_code == 404


def test_complete(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "a", "description": "b"}).json()

    response = client.post(f"/tasks/{created['id']}/complete")

    assert response.status_code == 200
    assert response.json()["completed"] is True


def test_complete_missing_returns_404(client: TestClient) -> None:
    response = client.post(f"/tasks/{uuid4()}/complete")

    assert response.status_code == 404


def test_delete(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "a", "description": "b"}).json()

    response = client.delete(f"/tasks/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_missing_returns_404(client: TestClient) -> None:
    response = client.delete(f"/tasks/{uuid4()}")

    assert response.status_code == 404
