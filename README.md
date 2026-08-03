# TEAF Reference App

Official reference application for the Torus Enterprise Application
Framework (TEAF). Version `0.1.0-alpha`.

## What this is

A minimal application whose only purpose is to demonstrate correct
consumption of TEAF's public API (`from teaf import Application`). It
contains no business logic, no CRUD, no authentication, and no database —
see `docs/BOOTSTRAP.md` for the full scope.

## ⚠ Known limitation

**TEAF (`v0.5.0-alpha`) does not currently expose a public `teaf` package
or an `Application` class.** `backend/app.py` is written exactly to the
target API this app is meant to consume, but it cannot be imported or run
until TEAF ships that package. This is documented in detail, with
evidence and a recommendation for TEAF's next sprint, in
[`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md).

What **does** work today: this repository installs cleanly, its
configuration layer (`backend/config.py`) is fully implemented and
tested, and the test suite runs green (passing config tests, cleanly
skipped app tests with an explicit reason).

## Install

```bash
pip install -e ".[dev]"
```

## Test

```bash
pytest -v
```

## Docs

- [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) — sprint scope and the TEAF
  limitation report.
- [`docs/PROJECT-STRUCTURE.md`](docs/PROJECT-STRUCTURE.md) — directory
  layout and rationale.
- [`docs/RUNNING.md`](docs/RUNNING.md) — install, test, lint, and run
  instructions, including expected results today vs. once TEAF ships its
  public API.
