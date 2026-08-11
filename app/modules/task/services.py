"""TaskService — all business logic for the Task Manager module lives here.

Routes stay thin on purpose: every rule below (what a valid title is, when
a transition is a conflict, which event a change publishes) belongs to the
service, so the same behaviour holds whether a caller arrives over HTTP or
calls the service directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from teaf import Event, EventBus

from app.modules.task import events
from app.modules.task.models import Task, TaskStatus
from app.modules.task.repository import TaskRepository

#: Bounds mirrored by the HTTP schemas, enforced here as well so a direct
#: service call cannot bypass them.
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 500


class TaskNotFoundError(Exception):
    """Raised when a task id has no matching `Task`."""


class TaskValidationError(Exception):
    """Raised when field values violate a domain rule."""


class TaskStatusConflictError(Exception):
    """Raised when a status transition conflicts with the task's current state."""


class TaskService:
    """Create, read, update, delete, and re-state tasks — the module's use cases.

    `events` is optional so unit tests can construct the service without a
    bus. In the running application `TaskModule` always supplies one; see
    that module's `configure` hook.
    """

    def __init__(self, repository: TaskRepository, events: EventBus | None = None) -> None:
        self._repository = repository
        self._events = events

    def create_task(self, *, title: str, description: str) -> Task:
        task = Task(
            title=_validated_title(title),
            description=_validated_description(description),
        )
        created = self._repository.add(task)
        self._publish(events.task_created(created))
        return created

    def get_task(self, task_id: UUID) -> Task:
        task = self._repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        return task

    def list_tasks(self) -> list[Task]:
        return self._repository.list()

    def update_task(self, task_id: UUID, *, title: str, description: str) -> Task:
        task = self.get_task(task_id)
        task.title = _validated_title(title)
        task.description = _validated_description(description)
        task.updated_at = datetime.now(UTC)
        updated = self._repository.update(task)
        self._publish(events.task_updated(updated))
        return updated

    def delete_task(self, task_id: UUID) -> None:
        task = self.get_task(task_id)
        if not self._repository.delete(task_id):
            raise TaskNotFoundError(str(task_id))
        self._publish(events.task_deleted(task))

    def change_status(self, task_id: UUID, status: TaskStatus) -> Task:
        """Move a task to `status`.

        Any transition between the three states is allowed — a task can be
        reopened after being finished, which is ordinary. Setting the status
        a task already has is rejected as a conflict rather than silently
        accepted, so a caller is never told a change happened when nothing
        did.
        """
        task = self.get_task(task_id)
        previous = task.status
        if previous is status:
            raise TaskStatusConflictError(f"Task is already {status.value}")
        task.status = status
        task.updated_at = datetime.now(UTC)
        updated = self._repository.update(task)
        self._publish(events.task_status_changed(updated, previous=previous))
        return updated

    def complete_task(self, task_id: UUID) -> Task:
        """Shorthand for moving a task to `DONE`. Conflicts if already done."""
        return self.change_status(task_id, TaskStatus.DONE)

    def _publish(self, event: Event) -> None:
        if self._events is not None:
            self._events.publish(event)


def _validated_title(title: str) -> str:
    return _validated_text(title, field="title", max_length=MAX_TITLE_LENGTH)


def _validated_description(description: str) -> str:
    return _validated_text(description, field="description", max_length=MAX_DESCRIPTION_LENGTH)


def _validated_text(value: str, *, field: str, max_length: int) -> str:
    stripped = value.strip()
    if not stripped:
        raise TaskValidationError(f"{field} must not be blank")
    if len(stripped) > max_length:
        raise TaskValidationError(f"{field} must be at most {max_length} characters")
    return stripped
