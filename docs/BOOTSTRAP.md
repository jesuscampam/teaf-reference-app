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

## TEAF Public API Limitation

**Finding:** as of TEAF `v0.5.0-alpha`, the framework does not expose a
`teaf` package or an `Application` class. This is a hard blocker for the
spec this sprint was given (`from teaf import Application`), and it is
documented here rather than worked around, per this sprint's own ground
rules (no workarounds, no copying TEAF's code, no modifying TEAF).

Evidence:

- There is no `teaf/` directory and no `teaf/__init__.py` anywhere in
  `torus-enterprise-framework`. `grep -rn "class Application"` across the
  whole repository returns zero matches.
- `torus-enterprise-framework/pyproject.toml` has no `[project]` and no
  `[build-system]` section, so the repository cannot be installed as a
  package named `teaf` (or anything else) via `pip install -e`. In this
  environment, `pip show teaf` and `python -c "import teaf"` both fail.
- The only currently working entry point is the internal
  `backend.core.application.create_app(settings=None) -> fastapi.FastAPI`,
  run via `uvicorn backend.main:app` — i.e. TEAF's own `backend.*`
  namespace, which this sprint explicitly forbids importing.
- TEAF's own source acknowledges this gap. `backend/main.py`'s docstring
  states (translated): *"while TEAF has no business modules to integrate,
  the bootstrap application itself serves as the minimal reference
  application."*
- The four endpoints required by this sprint (`/`, `/health`, `/info`,
  `/runtime/info`) **do** exist and work correctly inside TEAF today —
  they are just not reachable through any public `teaf` import.

**Consequence for this repository:** `backend/app.py` is written exactly
as the target public API is supposed to look
(`from teaf import Application`), so it will work unmodified the moment
TEAF ships that package. Until then:

- `import teaf` fails with `ModuleNotFoundError`.
- `backend/app.py` cannot be imported or run.
- `tests/test_app.py` skips (not fails) with an explicit reason.
- `mypy --strict` reports exactly one error, on the `teaf` import in
  `backend/app.py` — this is the intended, visible signature of the
  limitation, not a defect to silence.
- `backend/config.py` and its tests have no TEAF dependency and work
  fully today.

## Recommendation for TEAF's next sprint

Expose a public, installable `teaf` package (with a `[build-system]` in
`torus-enterprise-framework`'s `pyproject.toml`) that re-exports an
`Application` class wrapping `backend.core.application.create_app()`,
with a documented constructor signature (e.g. `name`, `version`,
`description`) and the ASGI app it wraps. That would let consumer
applications depend on `teaf` alone, matching the isolation this sprint
was designed around.
