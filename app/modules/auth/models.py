"""The demo account model.

This is a *demonstration* of TEAF's security API, not identity
management. There is no registration, no password reset, no lockout, no
audit trail, and no user database — two fixed accounts are created at
startup from configuration. What it does do honestly: store passwords
only as Argon2id hashes, and never compare them in clear.

Roles exist so the `403` path is real. `user` can change tasks; `viewer`
can only read them, which is what makes "authenticated but not allowed"
observable in the running application rather than only in a test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DemoRole(StrEnum):
    """The two roles this demo distinguishes."""

    USER = "user"
    VIEWER = "viewer"


class TaskPermission(StrEnum):
    """Permissions the Task API checks, granted through roles."""

    READ = "task.read"
    WRITE = "task.write"


#: Which permissions each role carries. `viewer` deliberately lacks
#: `task.write`, so every mutating endpoint answers `403` for it.
ROLE_PERMISSIONS: dict[DemoRole, frozenset[TaskPermission]] = {
    DemoRole.USER: frozenset({TaskPermission.READ, TaskPermission.WRITE}),
    DemoRole.VIEWER: frozenset({TaskPermission.READ}),
}


@dataclass(frozen=True, slots=True)
class DemoUser:
    """An account that can log in.

    `password_hash` is an Argon2id digest. The plain password is never a
    field on this object, so it cannot be logged, serialized, or returned
    by accident.
    """

    username: str
    password_hash: str
    roles: frozenset[DemoRole] = field(default_factory=frozenset)

    @property
    def permissions(self) -> frozenset[TaskPermission]:
        """Effective permissions, from this user's roles."""
        return frozenset(permission for role in self.roles for permission in ROLE_PERMISSIONS[role])
