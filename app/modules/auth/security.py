"""Assembles TEAF's security pieces into the objects this app installs.

Everything below comes from the public `teaf` package. The shape TEAF
asks for, and what each piece does:

    JWTProvider          issues / verifies / revokes tokens
        |
    JWTIdentityProvider  turns a Bearer credential into an Identity
        |
    IdentityProviderRegistry ─┐
                              ├─> SecurityMiddleware  (populates the
    PrincipalResolver ────────┘                        request's context)
        |
    StaticRoleResolver   role name -> Role(+permissions)

`SecurityMiddleware` **authenticates but does not enforce** — with no
credentials, or bad ones, it simply installs an anonymous context and lets
the request through. Enforcement is `@authorize()` on the endpoints, which
is the right split: the middleware has no idea which routes are public.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from teaf import (
    Argon2PasswordHasher,
    IdentityProviderRegistry,
    InMemoryTokenRevocationStore,
    JWTIdentityProvider,
    JWTProvider,
    Permission,
    PrincipalResolver,
    Role,
    StaticRoleResolver,
)

from app.config import AppSettings
from app.modules.auth.models import ROLE_PERMISSIONS
from app.modules.auth.repository import InMemoryUserRepository, build_demo_users
from app.modules.auth.services import AuthService


@dataclass(frozen=True, slots=True)
class SecurityComponents:
    """What `app/main.py` needs to install security, built in one place."""

    auth_service: AuthService
    provider_registry: IdentityProviderRegistry
    principal_resolver: PrincipalResolver
    users: InMemoryUserRepository


def build_security(settings: AppSettings) -> SecurityComponents:
    """Wire TEAF's security primitives for this application."""
    token_provider = JWTProvider(
        secret=_signing_secret(settings),
        issuer="teaf-reference-app",
        audience="teaf-reference-app",
        access_token_ttl_seconds=settings.auth_access_token_ttl_seconds,
        # Without a revocation store, `revoke()` has nowhere to record the
        # token and logout would only clear the browser's copy. In-memory
        # is right for a single-process demo; a shared store (TEAF ships a
        # Redis one) is what a multi-process deployment would need.
        revocation_store=InMemoryTokenRevocationStore(),
    )
    hasher = Argon2PasswordHasher()
    users = build_demo_users(settings, hasher)

    return SecurityComponents(
        auth_service=AuthService(users=users, hasher=hasher, tokens=token_provider),
        provider_registry=IdentityProviderRegistry(
            [JWTIdentityProvider(token_provider=token_provider)]
        ),
        principal_resolver=PrincipalResolver(
            role_resolver=StaticRoleResolver(roles_by_name=_roles())
        ),
        users=users,
    )


def _roles() -> dict[str, Role]:
    """The demo roles, as TEAF's `Role` objects keyed by claim name."""
    return {
        role.value: Role(
            name=role.value,
            permissions=frozenset(Permission(p.value) for p in permissions),
        )
        for role, permissions in ROLE_PERMISSIONS.items()
    }


def _signing_secret(settings: AppSettings) -> str:
    """The HS256 key, generated per process when none is configured.

    Shipping a default secret would mean shipping the ability to forge a
    token against every unconfigured deployment, so there isn't one. The
    trade-off is visible rather than hidden: with no `AUTH_JWT_SECRET`,
    every restart invalidates outstanding tokens and users log in again.

    TEAF rejects anything under 32 bytes (RFC 7518 §3.2), which is why the
    generated value is sized the way it is.
    """
    return settings.auth_jwt_secret or secrets.token_urlsafe(32)
