"""Tests for backend.config — no TEAF dependency, fully runnable today."""

from __future__ import annotations

import pytest

from backend.config import AppSettings, get_settings


def test_default_settings() -> None:
    settings = AppSettings()

    assert settings.app_name == "TEAF Reference App"
    assert settings.app_version == "0.1.0-alpha"
    assert settings.environment == "development"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Custom App")
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9000")

    settings = AppSettings()

    assert settings.app_name == "Custom App"
    assert settings.app_version == "9.9.9"
    assert settings.environment == "production"
    assert settings.host == "127.0.0.1"
    assert settings.port == 9000


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
