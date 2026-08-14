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

Handlers hold no business logic. Each one translates a domain exception
into a status code and nothing more:

    TaskNotFoundError       -> 404
    TaskValidationError     -> 400
    TaskStatusConflictError -> 409

Schema violations are rejected by FastAPI as 422 before a handler runs.
The `/tasks` prefix (not `/api/tasks`) is this repository's existing
convention, kept unchanged so no client breaks.

Every endpoint is protected with TEAF's public `@authorize(permission=...)`
decorator (Sprint A3). Reads need `task.read`, writes need `task.write`;
the framework's exception handler turns a missing token into `401` and a
missing permission into `403`, both with an RFC 7807 body, so nothing here
constructs those responses. The decorator sits *below* the router
decorator so FastAPI still sees the handler's real signature.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from teaf import authorize

from app.modules.task.models import TaskStatus
from app.modules.task.schemas import (
    ErrorResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskStatsResponse,
    TaskStatusUpdateRequest,
    TaskUpdateRequest,
)
from app.modules.task.services import (
    TaskNotFoundError,
    TaskService,
    TaskStatusConflictError,
    TaskValidationError,
)

# Documented error shapes, surfaced in the OpenAPI schema. Annotated with
# FastAPI's own parameter type: inferred, these would come out as
# `dict[int, ...]` and fail `--strict` against its `dict[int | str, ...]`.
_Responses = dict[int | str, dict[str, Any]]

#: Every endpoint here requires a token, and the mutating ones require a
#: permission the `viewer` role does not have — so `401` and `403` are
#: possible on all of them and are documented as such.
_AUTH: _Responses = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}
_BAD_REQUEST: _Responses = {**_AUTH, status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}}
_NOT_FOUND: _Responses = {**_AUTH, status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}
_NOT_FOUND_OR_INVALID: _Responses = {
    **_AUTH,
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
}
_NOT_FOUND_OR_CONFLICT: _Responses = {
    **_AUTH,
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_409_CONFLICT: {"model": ErrorResponse},
}

#: Permission names, mirroring app.modules.auth.models.TaskPermission. Kept
#: as literals so the Task module carries no import-time dependency on the
#: auth module; the two are joined only by the claim in the token.
_READ = "task.read"
_WRITE = "task.write"


def create_task_router(get_service: Callable[[], TaskService]) -> APIRouter:
    """Build the `/tasks` router, resolving `TaskService` per request via `get_service`."""
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.get("", response_model=list[TaskResponse])
    @authorize(permission=_READ)
    def list_tasks() -> list[TaskResponse]:
        return [TaskResponse.model_validate(task) for task in get_service().list_tasks()]

    @router.get("/stats", response_model=TaskStatsResponse)
    @authorize(permission=_READ)
    def task_stats() -> TaskStatsResponse:
        """Counts for the UI's metrics row.

        Declared before `/{task_id}` so Starlette matches the literal path
        first — otherwise "stats" would be parsed as a task id and 422.
        """
        tasks = get_service().list_tasks()
        by_status = [task.status for task in tasks]
        return TaskStatsResponse(
            total=len(tasks),
            todo=by_status.count(TaskStatus.TODO),
            in_progress=by_status.count(TaskStatus.IN_PROGRESS),
            done=by_status.count(TaskStatus.DONE),
        )

    @router.get("/{task_id}", response_model=TaskResponse, responses=_NOT_FOUND)
    @authorize(permission=_READ)
    def get_task(task_id: UUID) -> TaskResponse:
        try:
            task = get_service().get_task(task_id)
        except TaskNotFoundError as exc:
            raise _not_found() from exc
        return TaskResponse.model_validate(task)

    @router.post(
        "",
        response_model=TaskResponse,
        status_code=status.HTTP_201_CREATED,
        responses=_BAD_REQUEST,
    )
    @authorize(permission=_WRITE)
    def create_task(payload: TaskCreateRequest) -> TaskResponse:
        try:
            task = get_service().create_task(title=payload.title, description=payload.description)
        except TaskValidationError as exc:
            raise _bad_request(exc) from exc
        return TaskResponse.model_validate(task)

    @router.put("/{task_id}", response_model=TaskResponse, responses=_NOT_FOUND_OR_INVALID)
    @authorize(permission=_WRITE)
    def update_task(task_id: UUID, payload: TaskUpdateRequest) -> TaskResponse:
        try:
            task = get_service().update_task(
                task_id, title=payload.title, description=payload.description
            )
        except TaskNotFoundError as exc:
            raise _not_found() from exc
        except TaskValidationError as exc:
            raise _bad_request(exc) from exc
        return TaskResponse.model_validate(task)

    @router.patch(
        "/{task_id}/status", response_model=TaskResponse, responses=_NOT_FOUND_OR_CONFLICT
    )
    @authorize(permission=_WRITE)
    def change_status(task_id: UUID, payload: TaskStatusUpdateRequest) -> TaskResponse:
        try:
            task = get_service().change_status(task_id, payload.status)
        except TaskNotFoundError as exc:
            raise _not_found() from exc
        except TaskStatusConflictError as exc:
            raise _conflict(exc) from exc
        return TaskResponse.model_validate(task)

    @router.delete(
        "/{task_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_model=None,
        responses=_NOT_FOUND,
    )
    @authorize(permission=_WRITE)
    def delete_task(task_id: UUID) -> None:
        try:
            get_service().delete_task(task_id)
        except TaskNotFoundError as exc:
            raise _not_found() from exc

    @router.post(
        "/{task_id}/complete", response_model=TaskResponse, responses=_NOT_FOUND_OR_CONFLICT
    )
    @authorize(permission=_WRITE)
    def complete_task(task_id: UUID) -> TaskResponse:
        """Kept from Sprint A1 so existing clients keep working; equivalent to
        `PATCH /{id}/status` with `DONE`."""
        try:
            task = get_service().complete_task(task_id)
        except TaskNotFoundError as exc:
            raise _not_found() from exc
        except TaskStatusConflictError as exc:
            raise _conflict(exc) from exc
        return TaskResponse.model_validate(task)

    return router


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))
