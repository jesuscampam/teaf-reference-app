"""Application events published by the Task Manager module.

These are *application* events, not framework events: TEAF supplies the
transport (`teaf.Event`, `teaf.EventBus`, reachable from a module through
`ModuleContext.events`) and this module supplies the vocabulary. That
split is the thing worth demonstrating — an external application can put
its own domain events on the framework's bus without importing anything
private.

Payloads carry the task id, plus whatever a subscriber would otherwise
have to re-fetch the task to learn (its title, and for a status change,
both ends of the transition). They deliberately do not carry the whole
entity: an event is a notification, not a replication channel.
"""

from __future__ import annotations

from teaf import Event

from app.modules.task.models import Task, TaskStatus

TASK_CREATED = "task.created"
TASK_UPDATED = "task.updated"
TASK_STATUS_CHANGED = "task.status_changed"
TASK_DELETED = "task.deleted"

#: Every event name this module can publish — used by the runtime/events
#: view and by tests that assert the module's full event surface.
TASK_EVENT_NAMES: tuple[str, ...] = (
    TASK_CREATED,
    TASK_UPDATED,
    TASK_STATUS_CHANGED,
    TASK_DELETED,
)


def task_created(task: Task) -> Event:
    """A task was persisted for the first time."""
    return Event(
        name=TASK_CREATED,
        payload={"id": str(task.id), "title": task.title, "status": task.status.value},
    )


def task_updated(task: Task) -> Event:
    """A task's title or description changed."""
    return Event(
        name=TASK_UPDATED,
        payload={"id": str(task.id), "title": task.title},
    )


def task_status_changed(task: Task, *, previous: TaskStatus) -> Event:
    """A task moved between states. Carries both ends of the transition."""
    return Event(
        name=TASK_STATUS_CHANGED,
        payload={"id": str(task.id), "from": previous.value, "to": task.status.value},
    )


def task_deleted(task: Task) -> Event:
    """A task was removed. Carries the last known title, which is now gone."""
    return Event(
        name=TASK_DELETED,
        payload={"id": str(task.id), "title": task.title},
    )
