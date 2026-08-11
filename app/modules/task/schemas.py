"""Pydantic request/response schemas for the Task Manager HTTP API.

Kept separate from the domain `Task` dataclass on purpose: the wire format
is allowed to change without dragging the domain along, and vice versa.
Length bounds mirror the ones `TaskService` enforces, so bad input is
rejected at the edge with a 422 before any use case runs.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.task.models import TaskStatus
from app.modules.task.services import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH

_Title = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
_Description = Field(min_length=1, max_length=MAX_DESCRIPTION_LENGTH)


class TaskCreateRequest(BaseModel):
    """Payload for `POST /tasks`."""

    title: str = _Title
    description: str = _Description


class TaskUpdateRequest(BaseModel):
    """Payload for `PUT /tasks/{id}`."""

    title: str = _Title
    description: str = _Description


class TaskStatusUpdateRequest(BaseModel):
    """Payload for `PATCH /tasks/{id}/status`."""

    status: TaskStatus


class TaskResponse(BaseModel):
    """Serialized `Task`, returned by every Task Manager endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


class TaskStatsResponse(BaseModel):
    """Counts behind `GET /tasks/stats`, derived from persisted tasks only."""

    total: int
    todo: int
    in_progress: int
    done: int


class ErrorResponse(BaseModel):
    """The body every handled error returns.

    A single, predictable shape — `detail` is a human-readable sentence and
    nothing else. Exception types, tracebacks, and SQL never reach it.
    """

    detail: str
