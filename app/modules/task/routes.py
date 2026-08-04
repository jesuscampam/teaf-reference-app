"""FastAPI routes for the Task Manager module.

Built with a plain FastAPI `APIRouter`, mounted onto the running
`Application` via its public `.asgi` escape hatch (see app/main.py) — the
only TEAF-specific piece of this module is `module.py`; these routes are
ordinary FastAPI code bound to a `TaskService` instance.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.modules.task.schemas import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from app.modules.task.services import TaskNotFoundError, TaskService


def create_task_router(service: TaskService) -> APIRouter:
    """Build the `/tasks` router bound to a single `TaskService` instance."""
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.get("", response_model=list[TaskResponse])
    def list_tasks() -> list[TaskResponse]:
        return [TaskResponse.model_validate(task) for task in service.list_tasks()]

    @router.get("/{task_id}", response_model=TaskResponse)
    def get_task(task_id: UUID) -> TaskResponse:
        try:
            task = service.get_task(task_id)
        except TaskNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found") from exc
        return TaskResponse.model_validate(task)

    @router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
    def create_task(payload: TaskCreateRequest) -> TaskResponse:
        task = service.create_task(title=payload.title, description=payload.description)
        return TaskResponse.model_validate(task)

    @router.put("/{task_id}", response_model=TaskResponse)
    def update_task(task_id: UUID, payload: TaskUpdateRequest) -> TaskResponse:
        try:
            task = service.update_task(
                task_id, title=payload.title, description=payload.description
            )
        except TaskNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found") from exc
        return TaskResponse.model_validate(task)

    @router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
    def delete_task(task_id: UUID) -> None:
        try:
            service.delete_task(task_id)
        except TaskNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found") from exc

    @router.post("/{task_id}/complete", response_model=TaskResponse)
    def complete_task(task_id: UUID) -> TaskResponse:
        try:
            task = service.complete_task(task_id)
        except TaskNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found") from exc
        return TaskResponse.model_validate(task)

    return router
