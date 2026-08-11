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

    app_version: str = "0.3.0-alpha"

    #: Where the Task Manager's SQLite file lives (`TASK_DATABASE_PATH`).
    #: Relative paths resolve against the working directory the app is
    #: started from. `:memory:` is honoured and gives a throwaway database,
    #: which is what the test suite uses. TEAF exposes no database
    #: configuration of its own to defer to here — see
    #: app/modules/task/repository.py.
    task_database_path: str = "tasks.db"


@lru_cache
def get_settings() -> AppSettings:
    """Return the cached application settings."""
    return AppSettings()
