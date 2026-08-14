"""Application-level configuration for the TEAF Reference App.

Only `app_version` lives here. TEAF's own public `Configuration`
(`teaf.Configuration` / `teaf.get_configuration`, an alias of TEAF's
internal `Settings`) already exposes `app_name`, `environment`, `host`,
and `port` — reading the same environment variables this app used to
duplicate. Redeclaring those fields here would violate the "don't
duplicate TEAF's own configuration" rule this sprint is built around.
See docs/BOOTSTRAP.md.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Settings for the fields TEAF's own Configuration does not cover."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_version: str = "0.4.0-alpha"

    #: Where the Task Manager's SQLite file lives (`TASK_DATABASE_PATH`).
    #: Relative paths resolve against the working directory the app is
    #: started from. `:memory:` is honoured and gives a throwaway database,
    #: which is what the test suite uses. TEAF exposes no database
    #: configuration of its own to defer to here — see
    #: app/modules/task/repository.py.
    task_database_path: str = "tasks.db"

    # -- Demo authentication ---------------------------------------------------
    #
    # This app ships a *demonstration* login, not identity management. The
    # defaults below exist so `uvicorn app.main:app` works out of the box;
    # everything here is overridable, and none of it is a production secret.
    # See README, "Authentication", for the full limitations.

    #: HS256 signing key (`AUTH_JWT_SECRET`). **Left empty on purpose.** An
    #: empty value makes the app generate a random key at startup, so there
    #: is no shipped secret to leak and no default anybody could forge a
    #: token against. The cost is that tokens stop verifying across a
    #: restart — set this to keep sessions alive, and TEAF will reject
    #: anything shorter than 32 bytes (RFC 7518 §3.2).
    auth_jwt_secret: str = ""

    #: Demo account credentials (`AUTH_DEMO_USERNAME` / `AUTH_DEMO_PASSWORD`).
    #: Hashed with Argon2id at startup — never stored or compared in clear.
    auth_demo_username: str = "demo"
    auth_demo_password: str = "demo1234"

    #: A second, read-only account, so the 403 path is a real behaviour of
    #: the app rather than something only a test can reach.
    auth_viewer_username: str = "viewer"
    auth_viewer_password: str = "viewer1234"

    #: Access-token lifetime (`AUTH_ACCESS_TOKEN_TTL_SECONDS`). Short by
    #: default; the UI holds no refresh flow, so this is how long a browser
    #: session lasts before login is required again.
    auth_access_token_ttl_seconds: int = 3600


@lru_cache
def get_settings() -> AppSettings:
    """Return the cached application settings."""
    return AppSettings()
