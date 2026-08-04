"""Tests for app.config — this app's one non-duplicated setting."""

from __future__ import annotations

import pytest

from app.config import AppSettings, get_settings


def test_default_settings() -> None:
    settings = AppSettings()

    assert settings.app_version == "0.2.0-alpha"


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_VERSION", "9.9.9")

    settings = AppSettings()

    assert settings.app_version == "9.9.9"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
