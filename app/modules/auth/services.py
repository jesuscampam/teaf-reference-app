"""AuthService — login, logout, and the current session.

Every cryptographic operation here belongs to TEAF: `PasswordHasher`
(Argon2id) checks the password, `TokenProvider` (`JWTProvider`) issues,
verifies, and revokes tokens. This service only decides *who* may get a
token and what claims it carries.

Two behaviours are deliberate and worth stating:

**Failures are indistinguishable.** An unknown username and a wrong
password raise the same `InvalidCredentialsError` with the same message.
Telling them apart would turn the login form into an account-existence
oracle.

**A wrong username still costs a hash.** Looking up a missing account
returns immediately unless something verifies a password anyway, and that
timing difference is itself the oracle. `authenticate` therefore verifies
against a dummy hash when the user does not exist, so both paths do the
same work.
"""

from __future__ import annotations

from dataclasses import dataclass

from teaf import Claims, Identity, PasswordHasher, TokenPair, TokenProvider

from app.modules.auth.models import DemoUser
from app.modules.auth.repository import UserRepository

#: Identifies tokens minted by this application in `Identity.provider_id`.
PROVIDER_ID = "reference-app-demo"


class InvalidCredentialsError(Exception):
    """Raised when a username/password pair does not authenticate.

    Carries no detail about which half was wrong — see the module
    docstring.
    """


@dataclass(frozen=True, slots=True)
class LoginResult:
    """A successful login: the tokens, plus who they belong to.

    The identity travels with the tokens so the route can report roles and
    permissions without decoding the token it just issued.
    """

    tokens: TokenPair
    identity: Identity


class AuthService:
    """Turn credentials into a token, and a token back into nothing on logout."""

    def __init__(
        self,
        *,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenProvider,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        # Verified against when no account matches, so the failing path
        # costs the same as the succeeding one. Hashing a value nobody
        # knows is the point; the value itself is irrelevant.
        self._dummy_hash = hasher.hash("timing-equalizer-not-a-credential")

    async def login(self, username: str, password: str) -> LoginResult:
        """Authenticate and mint a token pair.

        Raises:
            InvalidCredentialsError: if the pair does not authenticate.
        """
        user = self._users.get_by_username(username)
        if user is None:
            self._hasher.verify(password, self._dummy_hash)
            raise InvalidCredentialsError("Invalid username or password")
        if not self._hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid username or password")
        identity = self._identity_for(user)
        return LoginResult(tokens=await self._tokens.issue(identity), identity=identity)

    async def logout(self, access_token: str) -> None:
        """Revoke a token server-side.

        Clearing the browser's copy alone would leave a token that still
        verifies for anyone who captured it; revoking means the server
        stops honouring it too.
        """
        await self._tokens.revoke(access_token)

    def _identity_for(self, user: DemoUser) -> Identity:
        """The claims a token carries. No password material, ever."""
        return Identity(
            id=user.username,
            provider_id=PROVIDER_ID,
            claims=Claims(
                sub=user.username,
                name=user.username,
                roles=frozenset(role.value for role in user.roles),
                permissions=frozenset(permission.value for permission in user.permissions),
            ),
        )
