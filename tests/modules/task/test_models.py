"""Tests for app.modules.task.models — no TEAF dependency."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.modules.task.models import Task, TaskStatus


def test_task_defaults() -> None:
    task = Task(title="Buy milk", description="2% milk")

    assert task.title == "Buy milk"
    assert task.description == "2% milk"
    assert task.status is TaskStatus.TODO
    assert isinstance(task.id, UUID)
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)


def test_task_ids_are_unique() -> None:
    first = Task(title="a", description="a")
    second = Task(title="b", description="b")

    assert first.id != second.id


def test_is_done_only_for_done_status() -> None:
    task = Task(title="a", description="a")

    assert task.is_done is False

    task.status = TaskStatus.IN_PROGRESS
    assert task.is_done is False

    task.status = TaskStatus.DONE
    assert task.is_done is True


def test_status_serializes_as_plain_string() -> None:
    """`StrEnum` is what lets the value cross HTTP and SQLite untouched."""
    assert TaskStatus.IN_PROGRESS == "IN_PROGRESS"
    assert f"{TaskStatus.DONE}" == "DONE"
