"""The Task entity — the Task Manager module's only domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class TaskStatus(StrEnum):
    """The three states a task can be in.

    A `StrEnum` so the value serializes to a plain string over HTTP and
    stores as a plain string in SQLite, with no converter on either side.
    Deliberately three states and no workflow engine: the point is to show
    a controlled domain vocabulary, not to model a real ticketing system.
    """

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


@dataclass(slots=True)
class Task:
    """A single task tracked by the Task Manager module."""

    title: str
    description: str
    status: TaskStatus = TaskStatus.TODO
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_done(self) -> bool:
        """Whether this task has reached its terminal state."""
        return self.status is TaskStatus.DONE
