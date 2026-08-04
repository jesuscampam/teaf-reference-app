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
    """Settings for the one field TEAF's own Configuration does not cover."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_version: str = "0.1.1-alpha"


@lru_cache
def get_settings() -> AppSettings:
    """Return the cached application settings."""
    return AppSettings()
