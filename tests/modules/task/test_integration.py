"""Integration tests: the Task module registered against the real Application.

Imports `app.main.app` directly — the same object `uvicorn app.main:app`
serves — so these exercise the actual module-registration wiring, not a
reconstruction of it.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_task_module_appears_in_runtime_info() -> None:
    response = client.get("/runtime/info")

    assert response.status_code == 200
    assert response.json()["registeredModules"] >= 8  # 7 TEAF built-ins + task


def test_task_module_appears_in_runtime_modules() -> None:
    response = client.get("/runtime/modules")

    assert response.status_code == 200
    assert "task" in {module["id"] for module in response.json()}


def test_task_capability_registered() -> None:
    response = client.get("/runtime/capabilities")

    assert response.status_code == 200
    assert "task.manage" in {capability["id"] for capability in response.json()}


def test_task_endpoints_work_through_real_app() -> None:
    created = client.post("/tasks", json={"title": "Integration", "description": "test"})
    assert created.status_code == 201

    task_id = created.json()["id"]
    assert client.get(f"/tasks/{task_id}").status_code == 200

    completed = client.post(f"/tasks/{task_id}/complete")
    assert completed.json()["completed"] is True

    assert client.delete(f"/tasks/{task_id}").status_code == 204
