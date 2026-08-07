"""Integration tests: the Task module registered against the real Application.

Uses the shared session-scoped `client` fixture (tests/conftest.py) —
same `app.main.app` singleton `uvicorn app.main:app` serves, so these
exercise the actual module-registration wiring, not a reconstruction of
it.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


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


def test_task_endpoints_work_through_real_app(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "Integration", "description": "test"})
    assert created.status_code == 201

    task_id = created.json()["id"]
    assert client.get(f"/tasks/{task_id}").status_code == 200

    completed = client.post(f"/tasks/{task_id}/complete")
    assert completed.json()["completed"] is True

    assert client.delete(f"/tasks/{task_id}").status_code == 204
