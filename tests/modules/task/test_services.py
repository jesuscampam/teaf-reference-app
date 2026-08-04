"""Tests for app.modules.task.services.TaskService."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.modules.task.repository import InMemoryTaskRepository
from app.modules.task.services import TaskNotFoundError, TaskService


@pytest.fixture
def service() -> TaskService:
    return TaskService(InMemoryTaskRepository())


def test_create_task(service: TaskService) -> None:
    task = service.create_task(title="a", description="b")

    assert task.title == "a"
    assert task.completed is False


def test_get_task(service: TaskService) -> None:
    created = service.create_task(title="a", description="b")

    assert service.get_task(created.id) is created


def test_get_task_missing_raises(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.get_task(uuid4())


def test_list_tasks(service: TaskService) -> None:
    service.create_task(title="a", description="a")
    service.create_task(title="b", description="b")

    assert len(service.list_tasks()) == 2


def test_update_task(service: TaskService) -> None:
    created = service.create_task(title="a", description="a")

    updated = service.update_task(created.id, title="new", description="new-desc")

    assert updated.title == "new"
    assert updated.description == "new-desc"
    assert updated.updated_at >= created.updated_at


def test_update_task_missing_raises(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.update_task(uuid4(), title="x", description="y")


def test_delete_task(service: TaskService) -> None:
    created = service.create_task(title="a", description="a")

    service.delete_task(created.id)

    with pytest.raises(TaskNotFoundError):
        service.get_task(created.id)


def test_delete_task_missing_raises(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.delete_task(uuid4())


def test_complete_task(service: TaskService) -> None:
    created = service.create_task(title="a", description="a")

    completed = service.complete_task(created.id)

    assert completed.completed is True


def test_complete_task_missing_raises(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.complete_task(uuid4())
