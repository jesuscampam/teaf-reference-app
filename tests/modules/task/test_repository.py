"""Tests for app.modules.task.repository.InMemoryTaskRepository."""

from __future__ import annotations

from uuid import uuid4

from app.modules.task.models import Task
from app.modules.task.repository import InMemoryTaskRepository


def test_add_and_get() -> None:
    repo = InMemoryTaskRepository()
    task = Task(title="a", description="b")

    repo.add(task)

    assert repo.get(task.id) is task


def test_get_missing_returns_none() -> None:
    repo = InMemoryTaskRepository()

    assert repo.get(uuid4()) is None


def test_list_returns_all_tasks() -> None:
    repo = InMemoryTaskRepository()
    first = Task(title="a", description="a")
    second = Task(title="b", description="b")
    repo.add(first)
    repo.add(second)

    assert {task.id for task in repo.list()} == {first.id, second.id}


def test_update_overwrites_existing() -> None:
    repo = InMemoryTaskRepository()
    task = Task(title="a", description="a")
    repo.add(task)

    task.title = "updated"
    repo.update(task)

    updated = repo.get(task.id)
    assert updated is not None
    assert updated.title == "updated"


def test_delete_returns_true_when_present() -> None:
    repo = InMemoryTaskRepository()
    task = Task(title="a", description="a")
    repo.add(task)

    assert repo.delete(task.id) is True
    assert repo.get(task.id) is None


def test_delete_returns_false_when_absent() -> None:
    repo = InMemoryTaskRepository()

    assert repo.delete(uuid4()) is False
