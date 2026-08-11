"""Tests for both `TaskRepository` implementations.

The contract tests run against each implementation via `parametrize`, so
the SQLite repository is held to exactly the same behaviour as the
in-memory one. `SqliteTaskRepository`'s own section then covers what only
it can do: keeping tasks across a restart.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from app.modules.task.models import Task, TaskStatus
from app.modules.task.repository import (
    InMemoryTaskRepository,
    SqliteTaskRepository,
    TaskRepository,
)

RepositoryFactory = Callable[[], TaskRepository]


@pytest.fixture(params=["in-memory", "sqlite"])
def repo(request: pytest.FixtureRequest) -> Iterator[TaskRepository]:
    if request.param == "in-memory":
        yield InMemoryTaskRepository()
        return
    sqlite_repo = SqliteTaskRepository(":memory:")
    yield sqlite_repo
    sqlite_repo.close()


def test_add_and_get(repo: TaskRepository) -> None:
    task = Task(title="a", description="b")

    repo.add(task)

    stored = repo.get(task.id)
    assert stored is not None
    assert stored.id == task.id
    assert stored.title == "a"


def test_get_missing_returns_none(repo: TaskRepository) -> None:
    assert repo.get(uuid4()) is None


def test_list_returns_all_tasks(repo: TaskRepository) -> None:
    first = Task(title="a", description="a")
    second = Task(title="b", description="b")
    repo.add(first)
    repo.add(second)

    assert {task.id for task in repo.list()} == {first.id, second.id}


def test_list_is_empty_initially(repo: TaskRepository) -> None:
    assert repo.list() == []


def test_update_overwrites_existing(repo: TaskRepository) -> None:
    task = Task(title="a", description="a")
    repo.add(task)

    task.title = "updated"
    task.status = TaskStatus.IN_PROGRESS
    repo.update(task)

    updated = repo.get(task.id)
    assert updated is not None
    assert updated.title == "updated"
    assert updated.status is TaskStatus.IN_PROGRESS


def test_delete_returns_true_when_present(repo: TaskRepository) -> None:
    task = Task(title="a", description="a")
    repo.add(task)

    assert repo.delete(task.id) is True
    assert repo.get(task.id) is None


def test_delete_returns_false_when_absent(repo: TaskRepository) -> None:
    assert repo.delete(uuid4()) is False


# -- SQLite only ---------------------------------------------------------------


def test_sqlite_tasks_survive_a_restart(tmp_path: Path) -> None:
    """The requirement that in-memory storage could never satisfy.

    Closing the repository and opening a new one over the same file is
    exactly what a process restart does to the database.
    """
    database = tmp_path / "tasks.db"
    task = Task(title="Persisted", description="still here after restart")

    with SqliteTaskRepository(database) as before_restart:
        before_restart.add(task)

    with SqliteTaskRepository(database) as after_restart:
        restored = after_restart.get(task.id)

    assert restored is not None
    assert restored.title == "Persisted"
    assert restored.status is TaskStatus.TODO


def test_sqlite_round_trips_every_field(tmp_path: Path) -> None:
    original = Task(title="t", description="d", status=TaskStatus.IN_PROGRESS)

    with SqliteTaskRepository(tmp_path / "tasks.db") as repository:
        repository.add(original)
        restored = repository.get(original.id)

    assert restored is not None
    assert restored.id == original.id
    assert restored.title == original.title
    assert restored.description == original.description
    assert restored.status is original.status
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_sqlite_timestamps_stay_timezone_aware(tmp_path: Path) -> None:
    """A naive datetime read back would break any later comparison."""
    task = Task(title="t", description="d")

    with SqliteTaskRepository(tmp_path / "tasks.db") as repository:
        repository.add(task)
        restored = repository.get(task.id)

    assert restored is not None
    assert restored.created_at.tzinfo is not None
    assert restored.updated_at.tzinfo is not None


def test_sqlite_creates_missing_parent_directories(tmp_path: Path) -> None:
    nested = tmp_path / "data" / "nested" / "tasks.db"

    with SqliteTaskRepository(nested):
        pass

    assert nested.exists()
