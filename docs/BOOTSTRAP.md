# Sprint A0 — Bootstrap

## Objective

Build the first official reference application for TEAF (Torus Enterprise
Application Framework), demonstrating that TEAF can be consumed cleanly
through its public API — `from teaf import Application` — and nothing else.

## Scope

This application:

- Does **not** contain business logic.
- Does **not** contain CRUD.
- Does **not** contain authentication.
- Does **not** contain a database.
- Exists only to demonstrate correct, minimal consumption of TEAF's public API.

TEAF itself is treated as an external dependency. Nothing in
`torus-enterprise-framework` is modified as part of this sprint, and this
application never imports TEAF's internal namespaces (`backend.*`,
`runtime.*`, `core.*`, `providers.*`, `contracts.*`, `sdk.*`).

## History: the TEAF public API gap, and its resolution

**At the time this sprint started, TEAF v0.5.0-alpha did not expose a
`teaf` package or an `Application` class.** `from teaf import Application`
was a hard blocker: no `teaf/` directory anywhere in
`torus-enterprise-framework`, no `[build-system]`/`[project]` in its
`pyproject.toml` (so it wasn't `pip install`-able as anything), and the
only working entry point was the internal
`backend.core.application.create_app()` — a namespace this sprint
explicitly forbids importing. Per this sprint's own ground rules (no
workarounds, no copying TEAF's code, no modifying TEAF), that gap was
documented rather than bypassed, and `app/main.py` (then `backend/app.py`)
was written exactly to the target public API shape so it would activate
unmodified the moment TEAF shipped it.

**TEAF shipped that public API in v0.6.1-alpha** (Sprint 2.5.1, "Public
SDK & Packaging"). `torus-enterprise-framework` now has a real
`[build-system]`/`[project]` (`name = "teaf"`), and `teaf/__init__.py`
exports `Application`, `Version`, `Runtime`, `Module`, `Configuration`,
and more — confirmed by installing it directly
(`pip install -e ../torus-enterprise-framework` → `teaf-0.6.1a0`) and
importing `from teaf import Application, Version` successfully.

## Why `app/`, not `backend/`

Adopting the real API surfaced a second, more fundamental problem than a
signature mismatch: **this repository's own top-level package was also
named `backend`**, identical to TEAF's internal, private namespace
(`backend.config`, `backend.core`, etc. — see TEAF's
`docs/public-api/IMPORT-GUIDE.md`, which documents `backend.*` as
private). Since both are regular Python packages (`__init__.py`, not
namespace packages), installing both in the same environment made one
shadow the other — and it was this repo's `backend/` that won, breaking
TEAF's own internal `from backend.config.settings import Settings` import
inside `teaf.application` with:

```
ModuleNotFoundError: No module named 'backend.config.settings'; 'backend.config' is not a package
```

This could not be fixed on TEAF's side without violating this sprint's
"never modify TEAF" rule, and TEAF is correct to keep `backend.*` private
regardless. The fix belongs entirely to this repository: the package was
renamed `backend/` → `app/`, and its entrypoint `app.py` → `main.py` (to
avoid the `app.app:app` redundancy and to mirror TEAF's own convention of
a `main.py` exposing `app`, run via `uvicorn app.main:app`). This is a
deliberate departure from Sprint A0's original instruction to create a
folder literally named `backend/` — a direct, documented consequence of
TEAF reserving that name for its own private implementation after A0 had
already used it.

## What consuming TEAF actually looks like today

```python
# app/main.py
from teaf import Application

app = Application()
```

`Application()` takes **no** `name`/`version`/`description` arguments —
its only parameter is an optional `settings: teaf.Configuration | None`
override. Naming, environment, host, and port are resolved from the
environment (`APP_NAME`, `ENVIRONMENT`, `HOST`, `PORT`) via TEAF's own
public `Configuration`/`get_configuration` (aliases of TEAF's internal
`Settings`/`get_settings`) — which is why `app/config.py` in this
repository no longer redeclares those four fields itself (that would
duplicate TEAF's own configuration, which this sprint explicitly
prohibits). It keeps only `app_version`, the one field that is genuinely
this application's own and has no TEAF equivalent — `Application.version`
returns TEAF's *framework* version, not the consuming app's.

`Application` implements the ASGI callable protocol directly
(`__call__(scope, receive, send)`), so an instance can be served as-is:
`uvicorn app.main:app` and `TestClient(app)` both just work.

## Endpoints

`/`, `/health`, `/info`, `/runtime/info` are provided entirely by TEAF —
this application defines no routes of its own. Verified end-to-end in
`docs/RUNNING.md`.
