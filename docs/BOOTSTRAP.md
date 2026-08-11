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

## Sprint A1.1 — TEAF v0.10.0-alpha Alignment + First Visual UI

Two things, neither changing this app's own version (`0.2.0-alpha` — no
new contract, per this sprint's own instruction not to bump arbitrarily):
align with TEAF's real public API as of v0.10.0-alpha (the proposal from
Sprint A1 above was implemented for real, under a different, better name
— see below), and add a small browser UI for the Task Manager.

### The workaround is gone — for real, not just relocated

TEAF v0.10.0-alpha's `Application` now accepts modules directly:

```python
# teaf/application.py
def __init__(self, settings=None, *, modules: Sequence[ModuleBase] | None = None) -> None: ...
def add_module(self, module: ModuleBase) -> Application: ...
```

Confirmed by reading `teaf/application.py` and `teaf/_internal/core/application.py`
directly (not assumed): modules passed via `modules=` are stored on
`app.state.pending_modules` and bootstrapped by `_bootstrap_pending_modules()`
*inside* TEAF's own `_lifespan()`, right alongside `Runtime.startup()` —
exactly the shape proposed in Sprint A1. `app/main.py` now reads:

```python
app = Application(modules=[TaskModule()])
```

No `threading.Thread`, no `asyncio.run()`, no manual `ModuleContext`
construction, no helper function that existed only for that workaround —
all removed. Verified with an AST-based import audit (not just `grep`)
across `app/` and `tests/`: zero references to `teaf._internal`, `backend.*`,
or any other private namespace; exactly two `from teaf import ...`
statements in the whole app (`app/main.py`, `app/modules/task/module.py`).

**One real consequence, not a workaround:** since module bootstrap now
happens *during* the lifespan instead of eagerly at import time,
`TaskService` isn't resolvable the instant `Application(...)` returns —
only once the lifespan has actually started. `app/modules/task/routes.py`
resolves it lazily, per request, via a small accessor function instead of
capturing a `TaskService` instance up front. This also means tests that
hit the real `app.main.app` must enter `TestClient(app)` as a context
manager (`with TestClient(app) as client:`) so the lifespan actually
runs — and, since `app.main.app` is a single process-wide object,
re-entering that context a *second* time (e.g. from a second test file
each creating their own `TestClient`) re-bootstraps `TaskModule` against
a `Runtime` that already has it registered, raising
`ModuleRegistrationException`. `tests/conftest.py` fixes this with one
session-scoped `client` fixture shared by every test file that needs a
live app — the lifespan starts once, is reused everywhere, and shuts
down once at the end of the run.

### First visual UI

`app/static/` (`index.html`, `styles.css`, `app.js`) — plain HTML/CSS/
vanilla JavaScript, no framework, no bundler, no Node.js/npm, served
directly by FastAPI's `StaticFiles` under `/static/*`, with `index.html`
served at `/` by one dedicated route. The UI holds no business logic: it
only calls the real `/tasks` endpoints and renders the response, with
loading/empty/error states. No mocks anywhere.

Two real integration issues surfaced only by testing this properly (not
just with `pytest`/`curl`, but by actually loading the page in a real
browser — see "Validation" below) — both resolved using only public API,
neither requiring a TEAF change:

1. **Route conflict at `/`.** TEAF's `create_app()` already registers
   `GET /` (a JSON status endpoint, from its health router) before this
   app ever gets `.asgi`. Starlette matches the *first* full
   `(path, method)` match in registration order, so a naively-added
   second `GET /` handler is permanently unreachable. Fix: register the
   UI route normally, then move just that one route to the front of
   `app.asgi.router.routes` — standard, fully public Starlette/FastAPI
   list manipulation (not a `teaf._internal` import), scoped to the
   single `/` path. `/health`, `/info`, `/runtime/*`, and `/tasks/*` are
   untouched (see `tests/test_ui.py`,
   `test_health_and_info_still_json_after_root_reorder`). Static assets
   are served under `/static/*` rather than mounted at `/`, specifically
   to avoid a second, worse version of the same problem: a
   `StaticFiles` mount at `/` would match *every* path as a fallback,
   silently shadowing `/health`, `/tasks`, etc. too.

2. **TEAF's default Content-Security-Policy blocks the UI's own assets.**
   TEAF's `SecurityHeadersMiddleware` (Sprint 2.9.2) sends
   `Content-Security-Policy: default-src 'none'` on every response by
   default — correct for a pure JSON API, and it never showed up in any
   `curl`- or `pytest`-based check, because CSP is enforced by browsers,
   not HTTP clients. Loading `http://localhost:8000/` in an actual
   Chromium instance (via Playwright, for this one verification step —
   not a project dependency, removed again afterward) showed the real
   symptom immediately: `styles.css` and `app.js` both refused to load,
   console errors citing the policy by name. Confirmed in
   `teaf/_internal/middleware/security_headers.py`'s own docstring that
   this is an intentional, *documented* override point: "a header the
   application already set is never overwritten." `app/main.py`'s `/`
   handler now sets its own `Content-Security-Policy: default-src 'self';
   frame-ancestors 'none'` — same-origin only, still restrictive, just
   not `'none'` — and TEAF's middleware backs off for that one response.
   Locked in as a regression test (`test_root_csp_allows_same_origin_assets`)
   so this doesn't require a real browser to catch next time.

### Validation

`pytest -v --cov=app`: 45/45 passed, 100% coverage across all of `app/`
(config, main, the Task Manager module, and the UI routes). `ruff` and
`black` clean. `mypy --strict app tests`: genuinely 0 findings — the two
external errors this surfaced (TEAF's own Redis-cache and LDAP-identity
provider modules, neither used by this app, referencing third-party
client libraries this app doesn't install) are handled with a
`[[tool.mypy.overrides]]` scoped to exactly `redis.*`/`ldap3.*`, not a
blanket suppression (see `pyproject.toml`). AST import audit: zero
forbidden imports in `app/` or `tests/`.

Real, non-mocked verification with `uvicorn app.main:app` actually
running: all four TEAF endpoints and all six `/tasks` endpoints checked
via `curl`, `task` confirmed in `/runtime/modules`/`/runtime/capabilities`
(same as Sprint A1) — and, going beyond `curl`, a full click-through of
the live UI in real Chromium (load → create → edit → complete → delete,
each step screenshotted, DOM/state asserted after each action, zero
unexpected console errors — the one `404` observed was the browser's own
automatic `/favicon.ico` request, unrelated to this app). This is what
caught the CSP issue above; a `curl`-only pass would have reported every
endpoint as `200 OK` while the UI was, in fact, completely broken in any
real browser.

## Sprint A2 — Persistence, events, and a controlled status model

Version `0.3.0-alpha`, built against TEAF `v0.10.3-alpha`.

The three previous sprints proved a business module can be registered
through TEAF's public SDK and driven from a browser. What they did not
prove is that anything *survives*: every task lived in a dictionary and
vanished with the process. This sprint closes that, adds the application's
own events to the framework's bus, and replaces the `completed` boolean
with a real, if small, status vocabulary.

### What was inspected before writing any code

The sprint brief described a repository that does not exist: a Sprint 3.5
frontend with `AppLayout`, `QueryBoundary`, `DataTable`, TanStack Query,
Zustand, and an `HttpClient`, plus authentication, a database, a
dashboard, and Runtime/Modules/Events screens to "preserve". None of that
is in this repository, and none of it is in TEAF either — the framework's
`frontend/` holds folder-structure `README.md` files and states that "el
shell de aplicación ejecutable se incorpora en la Versión 3 del roadmap".
What exists is what Sprint A1.1 left: 539 lines of vanilla HTML/CSS/JS.

So "extend the existing frontend, do not rebuild it" was honoured against
the frontend that actually exists. Building a React/Vite/npm toolchain
would have contradicted this repository's own standing constraint (no
framework, no bundler, no Node) recorded in the A1.1 section above.

### Persistence: why the application owns it

TEAF `v0.10.3-alpha` exports 213 public symbols. None of them is a
database: no `Database`, no `Session`, no `engine`, no repository base.
`teaf/_internal/database/` contains a single `README.md` describing an
intended SQLAlchemy/Alembic layer, with no implementation behind it.

There is therefore nothing to consume, and nothing to work around. Task
persistence is the Reference App's own concern, so
`SqliteTaskRepository` (`app/modules/task/repository.py`) uses the
standard library's `sqlite3` — **no new dependency in
`pyproject.toml`**. SQLAlchemy and Alembic are present in the environment
as transitive dependencies of `teaf`, but building on a transitive
install would be wrong, and an ORM plus a migration tool is a lot of
machinery for one table. Schema creation is one idempotent
`CREATE TABLE IF NOT EXISTS`; there is no migration framework here to
hook into and introducing one was out of scope.

`InMemoryTaskRepository` stays for unit tests, and both implementations
are held to the same contract by a parametrized test class, so the SQLite
one cannot quietly drift.

### Two TEAF findings, neither patched from this repository

**1. Concurrent first resolution of a singleton reports a cycle that
doesn't exist.** The new UI loads `/tasks` and `/tasks/stats` in
parallel. Starlette runs sync handlers in a thread pool, so both can be
the *first* request to resolve `TaskService`. When that happens TEAF's
container raises:

```
CircularDependencyException: Dependencia circular al resolver:
    TaskService -> TaskRepository -> TaskService
```

The graph has no cycle — `TaskService` depends on `TaskRepository`, which
depends on nothing. The container tracks its in-flight resolution chain in
state shared across threads, so one thread sees the other's partial chain
and mistakes it for recursion. It is a race, and it produced a real `500`
in a real browser.

*Affected API:* `Runtime.resolve_service` / the service container's cycle
detection. *Smallest fix that would be needed in TEAF:* make the
resolution chain thread-local (or guard singleton construction with a
per-registration lock) so concurrent resolution of the same contract
either blocks or reuses the in-flight instance instead of being reported
as recursion.

*Resolved application-side, without touching TEAF:* `TaskModule.ready()`
resolves its services during bootstrap, while startup is still
single-threaded. Every later request then gets the cached singleton and
never re-enters the factory. That is where singletons should be built
anyway, so this is not a workaround so much as the correct order —
`test_services_are_resolved_during_bootstrap` locks it in, and
`test_concurrent_requests_all_succeed` covers the request shape that
exposed it.

**2. Overriding `bootstrap()` with a synchronous method fails obscurely.**
`ModuleBase.bootstrap` is `async`, and `Application` does
`await module.bootstrap(context)`. A subclass that overrides it
synchronously gets `TypeError: object NoneType can't be used in 'await'
expression`, pointing into TEAF rather than at the override. The other
hooks are fine either way — `invoke_hook` accepts sync and async alike.
Not a defect, but a sharp edge: this module overrides `configure`,
`ready`, and `dispose` and leaves `bootstrap` alone. Worth a line in
TEAF's SDK documentation.

A third, smaller point, recorded because it shaped the tests: TEAF
publishes its own lifecycle events (`module.registered`,
`service.resolved`, …) onto the same bus. Assertions filter for the
application's own event names rather than comparing whole histories.

### Events

`ModuleContext.events` is the public route to the bus, captured in
`configure()` — which `ModuleBase.bootstrap` runs *before* it binds
services, so the bus is in place by the time the container can build a
`TaskService`. The service publishes `task.created`, `task.updated`,
`task.status_changed`, and `task.deleted`; payloads carry the id plus what
a subscriber would otherwise have to re-fetch, and nothing more. A test
subscribes a real handler and asserts it fires, so the bus is exercised as
pub/sub rather than as a log.

### Status model

`completed: bool` became `TaskStatus` (`TODO`, `IN_PROGRESS`, `DONE`), a
`StrEnum` so the value crosses HTTP and SQLite with no converter. Any
transition is allowed — reopening a finished task is ordinary — but
setting the status a task already has is a `409` rather than a silent
success, so a caller is never told something changed when nothing did.
`POST /{id}/complete` is kept for existing clients and is now exactly
`PATCH /{id}/status` with `DONE`.

`TaskResponse` returning `status` instead of `completed` is a breaking
change for any client written against `0.2.0-alpha`. It is recorded as
such in `CHANGELOG.md`.

### Frontend

`app/static/httpClient.js` is now the only place that calls `fetch`;
`app.js` imports `taskApi` from it. Native ES modules, so there is still
no bundler, no npm, and no Node — `index.html` just gained
`type="module"`. The client translates error bodies into one sentence
(`{"detail": ...}` and FastAPI's 422 array both), and the UI shows the
server's message rather than a generic one whenever there is one.

Counters come from `GET /tasks/stats`, not from arithmetic in the browser:
the numbers on screen are the server's, so there is no second
implementation to drift.

### What is deliberately absent

**Authentication.** TEAF has a full public security surface —
`JWTProvider`, `SecurityMiddleware`, `ApiProtectionModule`, `authorize`,
`current_identity`. None of it is wired up: every endpoint here is open.
The brief said to reuse the existing mechanism and not build a second one,
and there was no first one; adding login, token storage, and protected
routes reshapes the whole application and belongs in its own sprint. This
is a limitation, not an oversight.

**A JavaScript test runner.** The UI is covered by server-side tests and a
manual browser click-through. Adding Vitest/Jest means adding Node, which
this repository has consistently declined to do.

### Validation

`pytest`: **139 passed** (baseline for this sprint was 45). `ruff`,
`black`, and `mypy --strict app tests` all clean, with no new
`type: ignore`, `noqa`, or relaxed rule — the one typing fix needed was a
real annotation (`_Responses = dict[int | str, dict[str, Any]]`, matching
FastAPI's own parameter type), not a suppression. The AST import audit is
now an executable test rather than an ad-hoc script, and includes a case
proving the detector catches a planted violation.

Against a live `uvicorn app.main:app`: all six `/tasks` endpoints plus
`/tasks/stats`, the `409` and `404` paths, TEAF's five JSON endpoints, and
a full Chromium click-through (create → start → complete → edit → delete,
counters and status badges asserted after each step, zero console errors
beyond the browser's own `/favicon.ico` request).

Persistence was verified the only way that means anything: a task was
created against one `uvicorn` process, the process was killed, a second
process was started over the same database file, and the task came back
with its `IN_PROGRESS` status intact.
