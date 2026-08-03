"""Application-level configuration for the TEAF Reference App.

This module only configures this reference application (name, version,
environment, host, port). It does not duplicate TEAF's own internal
configuration (logging, docs toggles, etc.) — that remains TEAF's concern.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Environment-driven settings for the TEAF Reference App."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TEAF Reference App"
    app_version: str = "0.1.0-alpha"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> AppSettings:
    """Return the cached application settings."""
    return AppSettings()
