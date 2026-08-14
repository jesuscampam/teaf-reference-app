"""Request/response schemas for the auth endpoints.

`LoginResponse` carries the access token and nothing about the password.
There is intentionally **no refresh token in the response**: `JWTProvider`
issues one, but this app's UI has no refresh flow, and handing the browser
a long-lived credential it never uses would be a liability with no benefit.
When the access token expires the user logs in again.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Payload for `POST /auth/login`."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    """What a successful login returns."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    username: str
    roles: list[str]
    permissions: list[str]


class SessionResponse(BaseModel):
    """`GET /auth/me` — who the current token says you are."""

    username: str
    roles: list[str]
    permissions: list[str]
