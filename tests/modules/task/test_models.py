"""Tests for app.modules.task.models — no TEAF dependency."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.modules.task.models import Task


def test_task_defaults() -> None:
    task = Task(title="Buy milk", description="2% milk")

    assert task.title == "Buy milk"
    assert task.description == "2% milk"
    assert task.completed is False
    assert isinstance(task.id, UUID)
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)


def test_task_ids_are_unique() -> None:
    first = Task(title="a", description="a")
    second = Task(title="b", description="b")

    assert first.id != second.id
