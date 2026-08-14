"""Where the demo accounts live.

Deliberately in memory and deliberately tiny: this sprint demonstrates
TEAF's *security* API, and a user table would add persistence concerns
without adding anything to that demonstration. The accounts are built
once at startup from configuration, with passwords hashed on the way in.

Hashing at startup rather than shipping a digest keeps the configured
password out of the repository and lets an operator change it with an
environment variable alone.
"""

from __future__ import annotations

from typing import Protocol

from teaf import PasswordHasher

from app.config import AppSettings
from app.modules.auth.models import DemoRole, DemoUser


class UserRepository(Protocol):
    """Account lookup — the abstraction `AuthService` depends on."""

    def get_by_username(self, username: str) -> DemoUser | None: ...


class InMemoryUserRepository:
    """Holds the demo accounts for the life of the process."""

    def __init__(self, users: dict[str, DemoUser]) -> None:
        self._users = users

    def get_by_username(self, username: str) -> DemoUser | None:
        return self._users.get(username)


def build_demo_users(settings: AppSettings, hasher: PasswordHasher) -> InMemoryUserRepository:
    """Create the two demo accounts described in the README.

    `user` can read and write tasks; `viewer` can only read, which is what
    makes a `403` reachable from the browser.
    """
    accounts = (
        (settings.auth_demo_username, settings.auth_demo_password, DemoRole.USER),
        (settings.auth_viewer_username, settings.auth_viewer_password, DemoRole.VIEWER),
    )
    return InMemoryUserRepository(
        {
            username: DemoUser(
                username=username,
                password_hash=hasher.hash(password),
                roles=frozenset({role}),
            )
            for username, password, role in accounts
        }
    )
