# Project Structure

```
teaf-reference-app/
├── app/
│   ├── __init__.py
│   ├── config.py                 # This app's own settings: only `app_version`
│   ├── main.py                   # Application() + Task module registration + router mount
│   └── modules/
│       ├── __init__.py
│       └── task/                 # Task Manager — the reference business module
│           ├── __init__.py
│           ├── models.py         # Task entity (dataclass)
│           ├── repository.py     # TaskRepository (Protocol) + InMemoryTaskRepository
│           ├── services.py       # TaskService — all business logic
│           ├── schemas.py        # Pydantic request/response models
│           ├── routes.py         # FastAPI APIRouter — the 6 /tasks endpoints
│           └── module.py         # TaskModule(teaf.Module) — SDK registration
├── tests/
│   ├── __init__.py
│   ├── test_config.py            # app/config.py — no TEAF dependency
│   ├── test_app.py               # Application instantiation + the 4 TEAF endpoints
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
├── README.md
├── pyproject.toml
├── .gitignore
└── .env.example
```

## Rationale

- **`app/`** (not `backend/` — see `docs/BOOTSTRAP.md`, "Why `app/`, not
  `backend/`") holds only what this reference app owns: its own
  configuration, the entrypoint, and its business modules. No code here
  reimplements anything TEAF already provides.
- **`config.py`** intentionally does **not** redeclare
  `app_name`/`environment`/`host`/`port` — TEAF's own public
  `Configuration`/`get_configuration` already cover those, reading the
  same environment variables. Only `app_version` (this app's own version,
  distinct from TEAF's framework version) lives here.
- **`app/modules/task/`** follows Clean Architecture layering end to end:
  `models.py` (domain entity, no framework dependency) →
  `repository.py` (persistence contract + in-memory implementation,
  dependency-inverted — `TaskService` depends on the `TaskRepository`
  Protocol, never on `InMemoryTaskRepository` directly) → `services.py`
  (use cases, the only place with business logic) → `schemas.py` (HTTP
  DTOs, kept separate from the domain `Task` dataclass) → `routes.py`
  (thin FastAPI layer, no logic of its own) → `module.py` (the only file
  that imports `teaf.*` — registers services/capabilities/health checks
  via `ModuleBuilder`, per TEAF's public Module SDK).
- **`tests/`** mirrors `app/` one-to-one, plus `modules/task/` covering
  each Clean Architecture layer independently (model, repository,
  service, HTTP routes in isolation) and two module-specific concerns:
  SDK registration against a standalone `Runtime` (`test_module.py`) and
  integration against the real, wired `Application`
  (`test_integration.py`).
- **`docs/`** is kept to exactly the three files the original sprint
  called for — new sprints extend `BOOTSTRAP.md` rather than adding more
  files.
