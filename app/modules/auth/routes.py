"""FastAPI routes for authentication.

Three endpoints, and their protection is not uniform:

    POST /auth/login    public — you cannot require a token to get one
    POST /auth/logout   @authorize() — revoking needs a token to revoke
    GET  /auth/me       @authorize() — the session restore call

`@authorize()` is TEAF's public decorator. It raises the framework's own
authentication/authorization exceptions, which TEAF's exception handler
turns into `401`/`403` with an RFC 7807 body — so this module never builds
those responses by hand and never leaks an exception into one.

The bearer token is read from the `Authorization` header directly in
`logout`, because revocation needs the raw string and `current_identity()`
returns the decoded identity, not the token it came from.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from teaf import Identity, authorize, current_identity

from app.modules.auth.schemas import LoginRequest, LoginResponse, SessionResponse
from app.modules.auth.services import AuthService, InvalidCredentialsError
from app.modules.task.schemas import ErrorResponse

# Annotated with FastAPI's own parameter type; inferred it would be
# `dict[int, ...]` and fail `--strict`. Same reason as in task/routes.py.
_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}
}


def create_auth_router(get_service: Callable[[], AuthService]) -> APIRouter:
    """Build the `/auth` router, resolving `AuthService` per request."""
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/login", response_model=LoginResponse, responses=_UNAUTHORIZED)
    async def login(payload: LoginRequest) -> LoginResponse:
        try:
            result = await get_service().login(payload.username, payload.password)
        except InvalidCredentialsError as exc:
            # Same response for "no such user" and "wrong password" — see
            # AuthService's docstring. `str(exc)` is the service's own
            # fixed message, not an exception repr.
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

        session = _session_of(result.identity)
        return LoginResponse(
            access_token=result.tokens.access_token,
            token_type=result.tokens.token_type,
            expires_in=result.tokens.expires_in,
            username=session.username,
            roles=session.roles,
            permissions=session.permissions,
        )

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
    @authorize()
    async def logout(request: Request) -> None:
        token = _bearer_token(request)
        if token is not None:
            await get_service().logout(token)

    @router.get("/me", response_model=SessionResponse, responses=_UNAUTHORIZED)
    @authorize()
    def me() -> SessionResponse:
        return _session_of(current_identity())

    return router


def _session_of(identity: Identity) -> SessionResponse:
    return SessionResponse(
        username=identity.id,
        roles=sorted(identity.claims.roles),
        permissions=sorted(identity.claims.permissions),
    )


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    return token if scheme.lower() == "bearer" and token else None
