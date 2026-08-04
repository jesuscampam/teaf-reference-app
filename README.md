# TEAF Reference App

Official reference application for the Torus Enterprise Application
Framework (TEAF). Version `0.1.1-alpha`, built against TEAF `v0.6.1-alpha`.

## What this is

A minimal application whose only purpose is to demonstrate correct
consumption of TEAF's public API (`from teaf import Application`). It
contains no business logic, no CRUD, no authentication, and no database —
see [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) for the full scope, and for
the history of how this repo got here (TEAF didn't always have this
public API — see "History" in that doc).

## Install

```bash
pip install -e ../torus-enterprise-framework
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

Then verify: `curl http://localhost:8000/health`.

## Test

```bash
pytest -v
```

## Docs

- [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) — sprint scope, the TEAF
  public API history, and why this app's package is named `app/` and not
  `backend/`.
- [`docs/PROJECT-STRUCTURE.md`](docs/PROJECT-STRUCTURE.md) — directory
  layout and rationale.
- [`docs/RUNNING.md`](docs/RUNNING.md) — install, test, lint, run, and
  endpoint verification instructions.
