"""Pydantic request/response schemas for the Task Manager HTTP API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskCreateRequest(BaseModel):
    """Payload for `POST /tasks`."""

    title: str
    description: str


class TaskUpdateRequest(BaseModel):
    """Payload for `PUT /tasks/{id}`."""

    title: str
    description: str


class TaskResponse(BaseModel):
    """Serialized `Task`, returned by every Task Manager endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    completed: bool
    created_at: datetime
    updated_at: datetime
