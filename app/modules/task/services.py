"""TaskService — all business logic for the Task Manager module lives here."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.modules.task.models import Task
from app.modules.task.repository import TaskRepository


class TaskNotFoundError(Exception):
    """Raised when a task id has no matching `Task`."""


class TaskService:
    """Create, read, update, delete, and complete tasks — the module's use cases."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create_task(self, *, title: str, description: str) -> Task:
        task = Task(title=title, description=description)
        return self._repository.add(task)

    def get_task(self, task_id: UUID) -> Task:
        task = self._repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        return task

    def list_tasks(self) -> list[Task]:
        return self._repository.list()

    def update_task(self, task_id: UUID, *, title: str, description: str) -> Task:
        task = self.get_task(task_id)
        task.title = title
        task.description = description
        task.updated_at = datetime.now(UTC)
        return self._repository.update(task)

    def delete_task(self, task_id: UUID) -> None:
        if not self._repository.delete(task_id):
            raise TaskNotFoundError(str(task_id))

    def complete_task(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        task.completed = True
        task.updated_at = datetime.now(UTC)
        return self._repository.update(task)
