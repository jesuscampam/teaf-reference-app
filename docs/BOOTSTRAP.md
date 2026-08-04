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

## Sprint A0.1 — First Running Application (v0.1.1-alpha)

Sprint A0.1's brief asked, textually, for the top-level package to be
named `backend/` again (`backend/__init__.py`, `backend/main.py`,
`backend/config.py`, started via `uvicorn backend.main:app --reload`).
That is exactly the naming this repository moved away from in Sprint A0
(see "Why `app/`, not `backend/`" above), for a reason that is still
true today: `backend` is TEAF's own private, internal namespace.

Re-verified for this sprint before deciding: creating a top-level
`backend/__init__.py` in this repo again, with TEAF v0.6.1-alpha
installed in the same environment, still produces one of two bad
outcomes, deterministically, depending purely on `sys.path` ordering
between the two editable installs — not on anything this app's code
does:

1. This repo's `backend` package wins → TEAF's own
   `from backend.config.settings import Settings` (inside
   `teaf.application`) breaks with
   `ModuleNotFoundError: No module named 'backend.config.settings'`.
2. TEAF's `backend` package wins → `uvicorn backend.main:app` would
   resolve to **TEAF's own internal bootstrap app**
   (`torus-enterprise-framework/backend/main.py`, which also defines a
   module-level `app`), not this repository's code — a silent
   misdirection, worse than a crash, since it *looks* like it works.

Per this sprint's own "IMPORTANTE" clause (don't work around it, don't
modify TEAF, document the limitation and propose exactly what TEAF
should change), this repository keeps the `app/` layout from Sprint A0
rather than reintroducing `backend/`. Everything else in this sprint's
brief is otherwise satisfied: `Application` created solely via
`from teaf import Application`, no internal namespace imports, no
business logic/CRUD/persistence/auth, config limited to what TEAF
doesn't already cover, and the app started with `uvicorn app.main:app
--reload` (the one deviation from the literal spec, documented here).

**Proposal for a future TEAF sprint:** rename TEAF's own internal
implementation package away from the common, easily-collided name
`backend` — e.g. to a clearly private-marked name such as
`_teaf_internal/` or `teaf_backend/` — so that consumer applications
remain free to use conventional names like `backend/`, `app/`, or
`core/` for their own code without risking exactly this class of silent
or crashing collision. Until that happens, TEAF's own
`docs/public-api/IMPORT-GUIDE.md` should explicitly warn scaffolding
templates and new consumers away from naming their own top-level
package `backend` (or any of `runtime`, `core`, `contracts`,
`providers`, `sdk` — TEAF's other internal namespaces).

## Compatibility validation — TEAF v0.6.2-alpha

TEAF moved its internal implementation from a top-level `backend/`
package to `teaf._internal/` (Sprint 2.6.2), exactly the proposal noted
above — its own `[project] version` is now `0.6.2-alpha`, and the
public contract in `teaf/__init__.py` is unchanged (same fourteen
symbols plus companions). This repository was re-validated against it
with **zero code changes required**: `from teaf import Application,
Version` still resolve correctly, `app/main.py` still starts unmodified
via `uvicorn app.main:app --reload`, all four endpoints
(`/`, `/health`, `/info`, `/runtime/info`) still return `200` with live
data reflecting `frameworkVersion: "0.6.2-alpha"`, and the full test
suite (8/8), `ruff`, `black`, and `mypy --strict` all remain clean. As a
secondary confirmation: `import backend` now raises `ModuleNotFoundError`
in this environment — TEAF no longer claims that namespace at all, so
the collision risk documented under "Sprint A0.1" above is now
structurally impossible, independent of this repository's own naming.

Note: at validation time, this refactor existed on TEAF's
`claude/teaf-framework-architecture-v9a9bg` branch, not yet merged to
`main`.

## Sprint A1 — First Business Module: Task Manager (v0.2.0-alpha)

The first real business module built on TEAF: `app/modules/task/`, a
`Task` entity (`id`, `title`, `description`, `completed`, `created_at`,
`updated_at`), an `InMemoryTaskRepository` (no database — only to
validate the SDK), a `TaskService` with the six required operations, and
six HTTP endpoints (`GET/POST /tasks`, `GET/PUT/DELETE /tasks/{id}`,
`POST /tasks/{id}/complete`). Built entirely against TEAF's public Module
SDK (`teaf.Module`, `ModuleBuilder`, `ModuleContext`, `ModuleManifest`,
`Lifetime`, `CapabilityCategory`, `Health`) — verified via `grep` that
`app/` contains exactly two `teaf` imports, both from the public package
(`app/main.py`, `app/modules/task/module.py`), and zero references to
`teaf._internal.*` or any of TEAF's other internal namespaces.

### How module registration actually works

`TaskModule.get_manifest()` describes the module with `ModuleBuilder`;
the inherited `ModuleBase.bootstrap(context)` validates it, registers it
into the `Runtime`'s `ModuleRegistry`, and binds its services/capabilities
— exactly the flow demonstrated in TEAF's own
`examples/basic-module/main.py`. The only non-obvious part, discovered
by testing against a *running* `uvicorn` process rather than assuming
the example's manual-`Runtime` pattern would translate directly:

1. **`Application` has no way to accept modules at construction time** —
   `Application(settings=None)` is its only parameter. A consumer has to
   bootstrap their module against `app.runtime` themselves.
2. **TEAF's `create_app()` wires FastAPI's `lifespan` directly to
   `Runtime.startup()`/`shutdown()`** (`teaf/_internal/core/application.py`,
   `_lifespan`). Passing an explicit `lifespan=` to Starlette/FastAPI
   disables its `on_startup`/`on_shutdown` event-handler mechanism
   entirely (verified by reading `starlette.routing.Router.__init__`) —
   so `app.asgi.add_event_handler("startup", ...)` is silently never
   called. There is no public hook to run code before or during
   `Runtime.startup()`.
3. **The only remaining option is to bootstrap the module at import
   time**, before uvicorn starts serving. But `module.bootstrap()` is
   `async`, and `uvicorn app.main:app` imports the app string *from
   inside its own already-running event loop* (confirmed empirically:
   `asyncio.run()` at module level raised `RuntimeError: asyncio.run()
   cannot be called from a running event loop` the moment this was run
   under real `uvicorn`, despite working fine under a plain
   `python -c "..."` import). Running the bootstrap on a dedicated
   thread with its own fresh loop, then joining it, sidesteps this
   without depending on whether an outer loop happens to be running —
   see `app/main.py`.

This is a real gap in the public API, not a workaround for a missing
feature: `Application` and TEAF's Module SDK are both fully public and
used exactly as documented — there simply isn't a public, first-class way
to say "start this Application with these modules already registered."

**Proposal for a future TEAF sprint:** add a `modules` parameter to
`Application.__init__` (e.g. `Application(modules: Sequence[Module] =
()) `) that bootstraps each module *inside* `_lifespan`, before calling
`runtime.startup()` — so module registration participates in the same
async context TEAF already controls, and consumer code never needs to
reach for threads or worry about which event loop is active at import
time. This would remove the only genuinely awkward line in
`app/main.py`.

### Validation

`pytest -v --cov=app`: 40/40 passed, 100% coverage across `app/` (config,
main, and all six `task` module files). `ruff`, `black`, and
`mypy --strict` all clean (one narrow, standard `# type: ignore[type-abstract]`
on a single line in `module.py`, where `TaskRepository` — a `Protocol`,
used only as a dependency-injection key — is passed to
`ServiceContainer.resolve(contract: type[T])`; mypy's `type-abstract`
check assumes `type[T]` arguments must be instantiable, which doesn't
apply to container lookups by contract). Confirmed live via `uvicorn
app.main:app`: all six `/tasks` endpoints work end-to-end (create, list,
get, update, complete, delete, including a real 404 on a deleted task),
and `task` appears in `/info`, `/runtime/modules` (status `"implemented"`,
capability `"task.manage"`), and `/runtime/capabilities` alongside TEAF's
seven built-in `"contracts_only"` modules. `torus-enterprise-framework`
was not modified.
