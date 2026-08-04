"""In-memory persistence for the Task Manager module.

No database, per Sprint A1 scope — this exists only to validate that a
business module can declare and inject its own service contracts through
TEAF's public SDK (`ModuleBuilder.add_service`).
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.task.models import Task


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
