"""Tests for app.modules.auth.services.AuthService.

Built against the real `JWTProvider` and `Argon2PasswordHasher` from
`teaf` — the point of these tests is that TEAF's own primitives behave as
this application assumes, so substituting fakes would remove the thing
under test.

Argon2 is deliberately slow, so a module-scoped hasher and a small
account set keep the file from dominating the suite's runtime.
"""

from __future__ import annotations

import secrets

import pytest
from teaf import (
    Argon2PasswordHasher,
    InMemoryTokenRevocationStore,
    JWTProvider,
    PasswordHasher,
)

from app.modules.auth.models import DemoRole, DemoUser, TaskPermission
from app.modules.auth.repository import InMemoryUserRepository
from app.modules.auth.services import PROVIDER_ID, AuthService, InvalidCredentialsError

pytestmark = pytest.mark.anyio

USERNAME = "tester"
PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="module")
def hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


@pytest.fixture(scope="module")
def users(hasher: PasswordHasher) -> InMemoryUserRepository:
    return InMemoryUserRepository(
        {
            USERNAME: DemoUser(
                username=USERNAME,
                password_hash=hasher.hash(PASSWORD),
                roles=frozenset({DemoRole.USER}),
            )
        }
    )


@pytest.fixture
def tokens() -> JWTProvider:
    return JWTProvider(
        secret=secrets.token_urlsafe(32),
        revocation_store=InMemoryTokenRevocationStore(),
    )


@pytest.fixture
def service(
    users: InMemoryUserRepository, hasher: PasswordHasher, tokens: JWTProvider
) -> AuthService:
    return AuthService(users=users, hasher=hasher, tokens=tokens)


# -- Successful login ------------------------------------------------------------


async def test_login_returns_a_usable_token(service: AuthService, tokens: JWTProvider) -> None:
    result = await service.login(USERNAME, PASSWORD)

    verified = await tokens.verify(result.tokens.access_token)
    assert verified.id == USERNAME
    assert verified.authenticated is True


async def test_token_carries_roles_and_permissions(service: AuthService) -> None:
    result = await service.login(USERNAME, PASSWORD)

    assert result.identity.claims.roles == {DemoRole.USER.value}
    assert result.identity.claims.permissions == {
        TaskPermission.READ.value,
        TaskPermission.WRITE.value,
    }


async def test_identity_names_this_application_as_the_provider(service: AuthService) -> None:
    result = await service.login(USERNAME, PASSWORD)

    assert result.identity.provider_id == PROVIDER_ID


async def test_token_never_contains_password_material(service: AuthService) -> None:
    """A JWT payload is base64, not encryption — anything put in a claim is
    readable by whoever holds the token."""
    result = await service.login(USERNAME, PASSWORD)

    assert PASSWORD not in result.tokens.access_token
    assert "password" not in str(result.identity.claims.as_dict()).lower()


# -- Failed login ----------------------------------------------------------------


async def test_wrong_password_is_rejected(service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError):
        await service.login(USERNAME, "not-the-password")


async def test_unknown_user_is_rejected(service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError):
        await service.login("nobody", PASSWORD)


async def test_both_failures_are_indistinguishable(service: AuthService) -> None:
    """Different messages would turn the login form into an oracle for
    which usernames exist."""
    with pytest.raises(InvalidCredentialsError) as wrong_password:
        await service.login(USERNAME, "not-the-password")
    with pytest.raises(InvalidCredentialsError) as unknown_user:
        await service.login("nobody", PASSWORD)

    assert str(wrong_password.value) == str(unknown_user.value)


async def test_failure_message_names_neither_field(service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError) as failure:
        await service.login(USERNAME, "not-the-password")

    message = str(failure.value)
    assert USERNAME not in message
    assert PASSWORD not in message


# -- Logout ----------------------------------------------------------------------


async def test_logout_revokes_the_token(service: AuthService, tokens: JWTProvider) -> None:
    """Logout has to mean something server-side; clearing the browser's
    copy alone would leave a token that still verifies."""
    result = await service.login(USERNAME, PASSWORD)
    token = result.tokens.access_token
    await tokens.verify(token)

    await service.logout(token)

    # Matched on the message rather than the type: TEAF raises
    # `TokenRevokedException`, which lives in `teaf._internal` and is not
    # publicly exported, so a consumer cannot name it. Reported in
    # docs/BOOTSTRAP.md, "Sprint A3".
    with pytest.raises(Exception, match="revocad|revoked"):
        await tokens.verify(token)


async def test_logout_does_not_affect_other_sessions(
    service: AuthService, tokens: JWTProvider
) -> None:
    first = await service.login(USERNAME, PASSWORD)
    second = await service.login(USERNAME, PASSWORD)

    await service.logout(first.tokens.access_token)

    still_valid = await tokens.verify(second.tokens.access_token)
    assert still_valid.id == USERNAME
