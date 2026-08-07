"""FastAPI routes for the Task Manager module.

Built with a plain FastAPI `APIRouter`, mounted onto the running
`Application` via its public `.asgi` escape hatch (see app/main.py) — the
only TEAF-specific piece of this module is `module.py`; these routes are
ordinary FastAPI code bound to a `TaskService` accessor.

`create_task_router` takes a zero-argument `get_service` callable rather
than a `TaskService` instance directly: since Sprint A1.1, `TaskModule`
bootstraps during TEAF's ASGI lifespan (see `app/main.py`), not eagerly
at import time, so the service isn't resolvable yet when this router is
built — only once a request actually arrives (by which point the
lifespan has started). Each handler resolves it fresh per call.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.modules.task.schemas import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from app.modules.task.services import TaskNotFoundError, TaskService


def create_task_router(get_service: Callable[[], TaskService]) -> APIRouter:
    """Build the `/tasks` router, resolving `TaskService` per request via `get_service`."""
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.get("", response_model=list[TaskResponse])
    def list_tasks() -> list[TaskResponse]:
        return [TaskResponse.model_validate(task) for task in get_service().list_tasks()]

    @router.get("/{task_id}", response_model=TaskResponse)
    def get_task(task_id: UUID) -> TaskResponse:
        try:
            task = get_service().get_task(task_id)
        except TaskNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found") from exc
        return TaskResponse.model_validate(task)

    @router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
    def create_task(payload: TaskCreateRequest) -> TaskResponse:
        task = get_service().create_task(title=payload.title, description=payload.description)
        return TaskResponse.model_validate(task)

    @router.put("/{task_id}", response_model=TaskResponse)
    def update_task(task_id: UUID, payload: TaskUpdateRequest) -> TaskResponse:
        try:
            task = get_service().update_task(
                task_id, title=payload.title, description=payload.description
            )
        except TaskNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found") from exc
        return TaskResponse.model_validate(task)

    @router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
    def delete_task(task_id: UUID) -> None:
        try:
            get_service().delete_task(task_id)
        except TaskNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found") from exc

    @router.post("/{task_id}/complete", response_model=TaskResponse)
    def complete_task(task_id: UUID) -> TaskResponse:
        try:
            task = get_service().complete_task(task_id)
        except TaskNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found") from exc
        return TaskResponse.model_validate(task)

    return router
