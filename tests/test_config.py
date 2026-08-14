"""Tests for app.config — the settings TEAF's own Configuration doesn't cover."""

from __future__ import annotations

import pytest

from app.config import AppSettings, get_settings


def test_default_settings() -> None:
    settings = AppSettings()

    assert settings.app_version == "0.4.0-alpha"


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_VERSION", "9.9.9")

    settings = AppSettings()

    assert settings.app_version == "9.9.9"


def test_default_database_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """A relative file, so a plain `uvicorn app.main:app` just works.

    The variable is deleted first because tests/conftest.py sets it to
    `:memory:` for the whole session — without this the assertion would be
    reading the test harness's value, not the declared default.
    """
    monkeypatch.delenv("TASK_DATABASE_PATH", raising=False)

    assert AppSettings().task_database_path == "tasks.db"


def test_database_path_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASK_DATABASE_PATH", "/tmp/elsewhere.db")

    assert AppSettings().task_database_path == "/tmp/elsewhere.db"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
