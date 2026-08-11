# TEAF Reference App

Official reference application for the Torus Enterprise Application
Framework (TEAF). Version `0.3.0-alpha`, built against TEAF
`v0.10.3-alpha`.

## What this is

A small but real application demonstrating correct consumption of TEAF's
public API. It bootstraps via `from teaf import Application`, registers one
business module — **Task Manager**, built entirely against TEAF's public
Module SDK (`teaf.Module`, `ModuleBuilder`, `ModuleContext`) — publishes
its own application events on TEAF's event bus, persists tasks to SQLite,
and serves a browser UI for all of it. See
[`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) for the full scope and
sprint-by-sprint history, and [`CHANGELOG.md`](CHANGELOG.md) for the
release summary.

### What this Reference App proves

It is an **external consumer** of TEAF, in a separate repository, that
never imports `teaf._internal` (enforced by an AST scan in
`tests/test_public_api.py`, not by convention). Using only the published
API it gets: application lifecycle and ASGI wiring (`Application`),
module registration and DI (`Module`, `ModuleBuilder`, `Lifetime`),
capability and health registration, configuration, and an event bus
(`Event`, `EventBus` via `ModuleContext.events`). Everything the *business*
owns — the `Task` entity, its rules, its storage, its HTTP contract, and
its UI — lives here, not in the framework.

What it does **not** yet prove: authenticated access. TEAF's security API
is public and complete, but this app does not wire it up — every endpoint
is open. See "Known limitations" below.

## Requirements

- Python `>=3.11`
- A local checkout of `torus-enterprise-framework` as a sibling directory
  (`../torus-enterprise-framework`) — TEAF isn't published to any package
  index, so this is a manual editable install, not a `pyproject.toml`
  dependency (see the note in `pyproject.toml`).

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ../torus-enterprise-framework
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/** in a browser — the Task Manager UI loads
there directly. Tasks are written to `tasks.db` in the working directory
(override with `TASK_DATABASE_PATH`) and are still there after a restart.

## Test

```bash
pytest -v
```

## Task Manager UI

A deliberately simple browser UI (`app/static/`: plain HTML, CSS, and
vanilla JavaScript — no frontend framework, no bundler, no Node.js)
consuming the real `/tasks` API. No mocks: every button calls the actual
endpoint below. From the browser you can:

- View tasks, with loading / empty / error states
- Create a task
- Edit a task (inline)
- Move a task between `TODO`, `IN_PROGRESS`, and `DONE`
- Delete a task (with confirmation)
- See live counts per status

The UI holds no business logic — it only calls the API and renders the
response. All rules live in `TaskService`; all persistence in
`TaskRepository`; even the counters come from `GET /tasks/stats` rather
than being recomputed in the browser. Every request goes through the
shared client in `app/static/httpClient.js`, so no component calls `fetch`
directly. See [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) for the
TEAF-specific issues the UI surfaced across sprints — a
Content-Security-Policy that blocks the UI's own assets by default (A1.1),
and a container race under parallel requests (A2) — and how each was
resolved using only public API, without modifying the framework.

## Task Manager module

The reference module for authoring TEAF business modules: one entity
(`Task`: `id`, `title`, `description`, `status`, `created_at`,
`updated_at`, where `status` is `TODO` | `IN_PROGRESS` | `DONE`), a
SQLite-backed repository, one service (`TaskService`) holding every rule,
four application events on TEAF's bus, and seven HTTP endpoints. See
[`docs/PROJECT-STRUCTURE.md`](docs/PROJECT-STRUCTURE.md) for the module's
internal layout and [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) for how it
registers against TEAF's `Runtime` using only public API.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/tasks` | List all tasks |
| `GET` | `/tasks/{id}` | Get one task |
| `POST` | `/tasks` | Create a task |
| `PUT` | `/tasks/{id}` | Update a task |
| `DELETE` | `/tasks/{id}` | Delete a task |
| `PATCH` | `/tasks/{id}/status` | Move a task to a given status |
| `POST` | `/tasks/{id}/complete` | Shorthand for setting status `DONE` |
| `GET` | `/tasks/stats` | Counts per status, for the UI |

Status codes: `200`, `201` on create, `204` on delete, `400` for a domain
rule violation, `404` for an unknown id, `409` for a status that is
already set, `422` for a malformed payload. Errors return
`{"detail": "..."}` and never expose internals.

### Events

Published on TEAF's own bus (`ModuleContext.events`), alongside the
framework's own lifecycle events:

| Event | When |
|---|---|
| `task.created` | A task was persisted for the first time |
| `task.updated` | Title or description changed |
| `task.status_changed` | Carries both ends of the transition |
| `task.deleted` | Carries the last known title |

### Try it via curl

```bash
# Create
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk", "description": "2% milk, one gallon"}'

# List
curl http://localhost:8000/tasks

# Get one (replace <id> with the id from the create response)
curl http://localhost:8000/tasks/<id>

# Update
curl -X PUT http://localhost:8000/tasks/<id> \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy oat milk", "description": "unsweetened"}'

# Move between states
curl -X PATCH http://localhost:8000/tasks/<id>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "IN_PROGRESS"}'

# Complete (shorthand for status DONE)
curl -X POST http://localhost:8000/tasks/<id>/complete

# Counts per status
curl http://localhost:8000/tasks/stats

# Delete
curl -X DELETE http://localhost:8000/tasks/<id>
```

### Verify persistence

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Survives", "description": "restart me"}'

# Stop the server (Ctrl-C), start it again, then:
curl http://localhost:8000/tasks     # the task is still there
```

### Verify it's registered with TEAF's Runtime

```bash
curl http://localhost:8000/runtime/modules      # includes "task"
curl http://localhost:8000/runtime/capabilities # includes "task.manage"
curl http://localhost:8000/info                 # "task" listed with status "implemented"
```

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `APP_NAME` | `TEAF Reference App` | Read by TEAF's own `Configuration` |
| `ENVIRONMENT` | `development` | Read by TEAF's own `Configuration` |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Read by TEAF's own `Configuration` |
| `APP_VERSION` | `0.3.0-alpha` | This app's version, distinct from TEAF's |
| `TASK_DATABASE_PATH` | `tasks.db` | SQLite file; `:memory:` for a throwaway database |

`app/config.py` declares only the last two. The rest already belong to
TEAF's public `Configuration`, and redeclaring them would duplicate the
framework.

## Known limitations

- **No authentication.** Every endpoint is open. TEAF's public security
  API (`JWTProvider`, `SecurityMiddleware`, `ApiProtectionModule`) is
  complete and would support it; wiring it up reshapes the app and its UI,
  so it is deferred to its own sprint.
- **No migrations.** Schema creation is one idempotent
  `CREATE TABLE IF NOT EXISTS`. Fine for one table; not a migration story.
- **No JavaScript test runner.** The UI is covered by server-side tests
  and a manual browser click-through. Adding Vitest would mean adding
  Node, which this project has deliberately avoided.
- **SQLite, single connection, serialized by a lock.** Correct and simple
  at demo scale; not a concurrency story.

## Docs

- [`CHANGELOG.md`](CHANGELOG.md) — release summary per sprint.
- [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) — sprint-by-sprint history, the
  TEAF public API journey, and every documented limitation/decision along
  the way.
- [`docs/PROJECT-STRUCTURE.md`](docs/PROJECT-STRUCTURE.md) — directory
  layout and rationale, including the Task Manager module and UI.
- [`docs/RUNNING.md`](docs/RUNNING.md) — install, test, lint, run, and
  endpoint/UI verification instructions.
