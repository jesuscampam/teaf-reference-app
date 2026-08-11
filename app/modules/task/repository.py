"""Persistence for the Task Manager module.

Two implementations of one contract:

- `InMemoryTaskRepository` — dict-backed, used by unit tests that have no
  reason to touch a file.
- `SqliteTaskRepository` — the one the running application uses. Tasks
  survive a restart, which is the whole point of Sprint A2's persistence
  requirement.

**Why the app owns this and not TEAF.** TEAF v0.10.3-alpha exposes no
public database capability: there is no `Database`, `Session`, `engine`,
or repository base in the 213 symbols exported by `teaf` (verified by
inspecting the package), and `teaf/_internal/database/` contains a
`README.md` describing intent with no implementation behind it. Since the
framework offers nothing to consume here, persistence is the Reference
App's own concern — which is also how the sprint brief splits ownership
("The Reference App owns: Task persistence"). Nothing in this file is a
workaround for a missing TEAF API; it simply is not TEAF's job yet. See
docs/BOOTSTRAP.md, "Sprint A2".

`sqlite3` comes from the standard library, so persistence adds **no new
dependency** to `pyproject.toml`. SQLAlchemy and Alembic happen to be
installed as transitive dependencies of `teaf`, but depending on a
transitive install is not something this app should do, and a full ORM
plus a migration tool would be a large amount of machinery for one table.
Schema creation is a single idempotent `CREATE TABLE IF NOT EXISTS`;
there is no migration framework in this repository to hook into, and
introducing one for one table would be the kind of infrastructure the
sprint brief explicitly rules out.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.modules.task.models import Task, TaskStatus


class TaskRepository(Protocol):
    """Persistence contract for `Task` — the abstraction `TaskService` depends on."""

    def add(self, task: Task) -> Task: ...

    def get(self, task_id: UUID) -> Task | None: ...

    def list(self) -> list[Task]: ...

    def update(self, task: Task) -> Task: ...

    def delete(self, task_id: UUID) -> bool: ...


class InMemoryTaskRepository:
    """Extremely simple in-memory `TaskRepository` — dict-backed, nothing more."""

    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}

    def add(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    def get(self, task_id: UUID) -> Task | None:
        return self._tasks.get(task_id)

    def list(self) -> list[Task]:
        return list(self._tasks.values())

    def update(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    def delete(self, task_id: UUID) -> bool:
        return self._tasks.pop(task_id, None) is not None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""


class SqliteTaskRepository:
    """File-backed `TaskRepository`. Tasks outlive the process.

    One connection is held open for the repository's lifetime rather than
    opened per call, so `:memory:` databases (used by tests) keep their
    contents between operations instead of being discarded with each
    connection.

    `check_same_thread=False` plus an explicit `Lock` because Starlette
    runs sync route handlers in a thread pool: a connection created during
    module bootstrap will legitimately be used from a different worker
    thread on each request. The lock serializes access, which is correct
    here and costs nothing at this scale — the alternative (a connection
    per thread) would buy throughput this reference app has no use for.
    """

    def __init__(self, database_path: str | Path) -> None:
        self._path = str(database_path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._lock, self._connection:
            self._connection.execute(_SCHEMA)

    def close(self) -> None:
        """Close the underlying connection. Safe to call more than once."""
        self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def add(self, task: Task) -> Task:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO tasks (id, title, description, status, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                _to_row(task),
            )
        return task

    def get(self, task_id: UUID) -> Task | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (str(task_id),)
            ).fetchone()
        return None if row is None else _from_row(row)

    def list(self) -> list[Task]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM tasks ORDER BY created_at").fetchall()
        return [_from_row(row) for row in rows]

    def update(self, task: Task) -> Task:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE tasks SET title = ?, description = ?, status = ?, updated_at = ?"
                " WHERE id = ?",
                (
                    task.title,
                    task.description,
                    task.status.value,
                    task.updated_at.isoformat(),
                    str(task.id),
                ),
            )
        return task

    def delete(self, task_id: UUID) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute("DELETE FROM tasks WHERE id = ?", (str(task_id),))
        return cursor.rowcount > 0


def _to_row(task: Task) -> tuple[str, str, str, str, str, str]:
    return (
        str(task.id),
        task.title,
        task.description,
        task.status.value,
        task.created_at.isoformat(),
        task.updated_at.isoformat(),
    )


def _from_row(row: sqlite3.Row) -> Task:
    return Task(
        id=UUID(row["id"]),
        title=row["title"],
        description=row["description"],
        status=TaskStatus(row["status"]),
        created_at=_parse_timestamp(row["created_at"]),
        updated_at=_parse_timestamp(row["updated_at"]),
    )


def _parse_timestamp(value: str) -> datetime:
    """Read back a stored ISO-8601 timestamp, always timezone-aware.

    Rows written by this repository always carry an offset, since `Task`
    defaults to `datetime.now(UTC)`. The `tzinfo` fallback covers a row
    edited by hand or by an older build, so a naive value can never leak
    into the domain and blow up a later comparison.
    """
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
