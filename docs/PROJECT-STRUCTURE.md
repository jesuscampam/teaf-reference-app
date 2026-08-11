# Project Structure

```
teaf-reference-app/
├── app/
│   ├── __init__.py
│   ├── config.py                 # This app's own settings: app_version, task_database_path
│   ├── main.py                   # Application(modules=[...]) + UI route + router mount
│   ├── static/                   # The Task Manager UI — plain HTML/CSS/JS, no framework
│   │   ├── index.html
│   │   ├── styles.css
│   │   ├── httpClient.js         # The only file that calls fetch — shared API client
│   │   └── app.js                # Rendering and view state only
│   └── modules/
│       ├── __init__.py
│       └── task/                 # Task Manager — the reference business module
│           ├── __init__.py
│           ├── models.py         # Task entity + TaskStatus (TODO/IN_PROGRESS/DONE)
│           ├── repository.py     # TaskRepository (Protocol) + InMemory + Sqlite
│           ├── services.py       # TaskService — all business logic
│           ├── events.py         # The module's own events, built on teaf.Event
│           ├── schemas.py        # Pydantic request/response models
│           ├── routes.py         # FastAPI APIRouter — the 7 /tasks endpoints
│           └── module.py         # TaskModule(teaf.Module) — SDK registration
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Shared session-scoped `client` fixture — see its docstring
│   ├── test_config.py            # app/config.py — no TEAF dependency
│   ├── test_app.py               # Application instantiation + the 4 TEAF endpoints
│   ├── test_ui.py                # GET /, static assets, the CSP override
│   ├── test_public_api.py        # Public-API boundary: AST scan for private imports
│   └── modules/task/
│       ├── test_models.py
│       ├── test_repository.py
│       ├── test_services.py
│       ├── test_routes.py        # HTTP layer, isolated FastAPI app
│       ├── test_module.py        # Manifest validity + bootstrap() against a standalone Runtime
│       └── test_integration.py   # Registered against the real app.main.app
├── docs/
│   ├── BOOTSTRAP.md               # Sprint-by-sprint history and every documented decision/limitation
│   ├── PROJECT-STRUCTURE.md       # This file
│   └── RUNNING.md                 # Install / test / lint / run instructions
├── CHANGELOG.md
├── README.md
├── pyproject.toml
├── .gitignore
└── .env.example
```

## Rationale

- **`app/`** (not `backend/` — see `docs/BOOTSTRAP.md`, "Why `app/`, not
  `backend/`") holds only what this reference app owns: its own
  configuration, the entrypoint, its business modules, and the UI. No
  code here reimplements anything TEAF already provides.
- **`config.py`** intentionally does **not** redeclare
  `app_name`/`environment`/`host`/`port` — TEAF's own public
  `Configuration`/`get_configuration` already cover those, reading the
  same environment variables. Only two settings live here: `app_version`
  (this app's own version, distinct from TEAF's framework version) and
  `task_database_path`, which has no TEAF counterpart to defer to because
  the framework exposes no database configuration at all.
- **`app/static/`** is plain HTML/CSS/vanilla JS, served by FastAPI's
  `StaticFiles` (`/static/*`) plus one dedicated route for `index.html`
  at `/` (see `app/main.py` and `docs/BOOTSTRAP.md`, "Sprint A1.1", for
  why `/` needs a one-line route reorder and its own
  `Content-Security-Policy` header). No build step, no bundler, no
  framework. The split inside it matters: `httpClient.js` owns every
  network call and error translation, `app.js` owns rendering and view
  state and calls `fetch` nowhere. Native ES modules connect the two, so
  the separation costs no tooling.
- **`app/modules/task/`** follows Clean Architecture layering end to end:
  `models.py` (domain entity, no framework dependency) →
  `repository.py` (persistence contract + two implementations,
  dependency-inverted — `TaskService` depends on the `TaskRepository`
  Protocol, never on `SqliteTaskRepository` or `InMemoryTaskRepository`
  directly; see that file for why persistence is the app's job and not
  TEAF's) → `services.py` (use cases, the only place with business logic,
  and the only place that publishes events) → `events.py` (the module's
  own event vocabulary, carried on TEAF's bus) → `schemas.py` (HTTP
  DTOs, kept separate from the domain `Task` dataclass) → `routes.py`
  (thin FastAPI layer, no logic of its own — resolves `TaskService` per
  request, since module bootstrap now happens during TEAF's lifespan, not
  at import time) → `module.py` (the only file besides `main.py` that
  imports `teaf.*` — registers services/capabilities/health checks via
  `ModuleBuilder`, per TEAF's public Module SDK).
- **`tests/`** mirrors `app/` one-to-one, plus `modules/task/` covering
  each Clean Architecture layer independently (model, repository,
  service, HTTP routes in isolation) and two module-specific concerns:
  SDK registration against a standalone `Runtime` (`test_module.py`) and
  integration against the real, wired `Application` (`test_integration.py`,
  `test_ui.py`). `conftest.py`'s session-scoped `client` fixture is what
  makes sharing one live `Application` across those files safe.
- **`docs/`** is kept to exactly the three files the original sprint
  called for — new sprints extend `BOOTSTRAP.md` rather than adding more
  files.
