"""Tests for app.modules.task.services.TaskService.

Two fixtures on purpose: `service` for the plain use cases, and
`service_with_events` where a real `teaf.EventBus` is attached so the
published events can be read back from `bus.history()`. The bus is TEAF's
own public class — these tests assert against the real thing, not a stub.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from teaf import EventBus

from app.modules.task import events
from app.modules.task.models import TaskStatus
from app.modules.task.repository import InMemoryTaskRepository
from app.modules.task.services import (
    MAX_TITLE_LENGTH,
    TaskNotFoundError,
    TaskService,
    TaskStatusConflictError,
    TaskValidationError,
)


@pytest.fixture
def service() -> TaskService:
    return TaskService(InMemoryTaskRepository())


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def service_with_events(bus: EventBus) -> TaskService:
    return TaskService(InMemoryTaskRepository(), bus)


# -- Use cases -----------------------------------------------------------------


def test_create_task(service: TaskService) -> None:
    task = service.create_task(title="a", description="b")

    assert task.title == "a"
    assert task.status is TaskStatus.TODO


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
    assert updated.updated_at >= created.created_at


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


# -- Status transitions --------------------------------------------------------


@pytest.mark.parametrize("target", [TaskStatus.IN_PROGRESS, TaskStatus.DONE])
def test_change_status_moves_task(service: TaskService, target: TaskStatus) -> None:
    created = service.create_task(title="a", description="a")

    changed = service.change_status(created.id, target)

    assert changed.status is target


def test_change_status_can_reopen_a_finished_task(service: TaskService) -> None:
    created = service.create_task(title="a", description="a")
    service.complete_task(created.id)

    reopened = service.change_status(created.id, TaskStatus.TODO)

    assert reopened.status is TaskStatus.TODO


def test_change_status_to_current_status_is_a_conflict(service: TaskService) -> None:
    created = service.create_task(title="a", description="a")

    with pytest.raises(TaskStatusConflictError):
        service.change_status(created.id, TaskStatus.TODO)


def test_change_status_missing_raises(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.change_status(uuid4(), TaskStatus.DONE)


def test_complete_task(service: TaskService) -> None:
    created = service.create_task(title="a", description="a")

    completed = service.complete_task(created.id)

    assert completed.status is TaskStatus.DONE
    assert completed.is_done is True


def test_complete_task_twice_is_a_conflict(service: TaskService) -> None:
    created = service.create_task(title="a", description="a")
    service.complete_task(created.id)

    with pytest.raises(TaskStatusConflictError):
        service.complete_task(created.id)


def test_complete_task_missing_raises(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.complete_task(uuid4())


# -- Validation ----------------------------------------------------------------


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_create_rejects_blank_title(service: TaskService, blank: str) -> None:
    with pytest.raises(TaskValidationError):
        service.create_task(title=blank, description="ok")


def test_create_rejects_blank_description(service: TaskService) -> None:
    with pytest.raises(TaskValidationError):
        service.create_task(title="ok", description="  ")


def test_create_rejects_overlong_title(service: TaskService) -> None:
    with pytest.raises(TaskValidationError):
        service.create_task(title="x" * (MAX_TITLE_LENGTH + 1), description="ok")


def test_create_trims_surrounding_whitespace(service: TaskService) -> None:
    task = service.create_task(title="  padded  ", description="  also  ")

    assert task.title == "padded"
    assert task.description == "also"


def test_update_rejects_blank_title(service: TaskService) -> None:
    created = service.create_task(title="a", description="a")

    with pytest.raises(TaskValidationError):
        service.update_task(created.id, title=" ", description="ok")


# -- Events --------------------------------------------------------------------


def test_create_publishes_task_created(service_with_events: TaskService, bus: EventBus) -> None:
    task = service_with_events.create_task(title="a", description="b")

    published = bus.history()
    assert [event.name for event in published] == [events.TASK_CREATED]
    assert published[0].payload["id"] == str(task.id)
    assert published[0].payload["title"] == "a"


def test_update_publishes_task_updated(service_with_events: TaskService, bus: EventBus) -> None:
    task = service_with_events.create_task(title="a", description="b")

    service_with_events.update_task(task.id, title="renamed", description="b")

    assert [event.name for event in bus.history()] == [
        events.TASK_CREATED,
        events.TASK_UPDATED,
    ]


def test_status_change_publishes_both_ends_of_the_transition(
    service_with_events: TaskService, bus: EventBus
) -> None:
    task = service_with_events.create_task(title="a", description="b")

    service_with_events.change_status(task.id, TaskStatus.IN_PROGRESS)

    status_event = bus.history()[-1]
    assert status_event.name == events.TASK_STATUS_CHANGED
    assert status_event.payload["from"] == "TODO"
    assert status_event.payload["to"] == "IN_PROGRESS"


def test_delete_publishes_task_deleted(service_with_events: TaskService, bus: EventBus) -> None:
    task = service_with_events.create_task(title="doomed", description="b")

    service_with_events.delete_task(task.id)

    deleted_event = bus.history()[-1]
    assert deleted_event.name == events.TASK_DELETED
    assert deleted_event.payload["title"] == "doomed"


def test_a_subscriber_receives_published_events(
    service_with_events: TaskService, bus: EventBus
) -> None:
    """The bus is a real pub/sub, not just a log — prove a handler runs."""
    received: list[str] = []
    bus.subscribe(events.TASK_CREATED, lambda event: received.append(str(event.payload["title"])))

    service_with_events.create_task(title="observed", description="b")

    assert received == ["observed"]


def test_failed_operations_publish_nothing(service_with_events: TaskService, bus: EventBus) -> None:
    with pytest.raises(TaskValidationError):
        service_with_events.create_task(title="", description="b")
    with pytest.raises(TaskNotFoundError):
        service_with_events.delete_task(uuid4())

    assert bus.history() == ()


def test_service_without_a_bus_still_works(service: TaskService) -> None:
    """Events are optional wiring; the use cases must not depend on them."""
    task = service.create_task(title="a", description="b")

    assert service.complete_task(task.id).status is TaskStatus.DONE


def test_delete_reports_not_found_if_the_row_vanishes_mid_call() -> None:
    """Covers the guard between `get_task` and the repository's `delete`.

    Unreachable through a single-threaded path — `get_task` would have
    raised already — but two callers deleting the same task can interleave
    there, and the second must get `TaskNotFoundError` rather than a
    spurious success and a `task.deleted` event for a task it didn't
    delete.
    """

    class VanishingRepository(InMemoryTaskRepository):
        def delete(self, task_id: UUID) -> bool:
            return False

    bus = EventBus()
    service = TaskService(VanishingRepository(), bus)
    task = service.create_task(title="a", description="b")

    with pytest.raises(TaskNotFoundError):
        service.delete_task(task.id)

    assert [event.name for event in bus.history()] == [events.TASK_CREATED]
