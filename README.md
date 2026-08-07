# TEAF Reference App

Official reference application for the Torus Enterprise Application
Framework (TEAF). Version `0.2.0-alpha`, built against TEAF
`v0.10.0-alpha`.

## What this is

A minimal application demonstrating correct consumption of TEAF's public
API. It bootstraps via `from teaf import Application`, registers one real
business module — **Task Manager**, built entirely against TEAF's public
Module SDK (`teaf.Module`, `ModuleBuilder`, `ModuleContext`) — and, as of
Sprint A1.1, serves a small browser UI for it. No database, no auth, no
business logic beyond simple CRUD on a `Task` entity. See
[`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) for the full scope and
sprint-by-sprint history.

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
there directly.

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
- Complete a task
- Delete a task (with confirmation)

The UI holds no business logic — it only calls the API and renders the
response. All rules live in `TaskService`; all persistence in
`TaskRepository`. See [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) ("Sprint
A1.1") for the two TEAF-specific issues this surfaced (module bootstrap
timing, and a Content-Security-Policy header that blocks the UI's own
assets by default) and how each was resolved using only public API.

## Task Manager module

The reference module for authoring TEAF business modules: one entity
(`Task`: `id`, `title`, `description`, `completed`, `created_at`,
`updated_at`), one in-memory repository (no database), one service
(`TaskService`), and six HTTP endpoints. See
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
| `POST` | `/tasks/{id}/complete` | Mark a task as completed |

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

# Complete
curl -X POST http://localhost:8000/tasks/<id>/complete

# Delete
curl -X DELETE http://localhost:8000/tasks/<id>
```

### Verify it's registered with TEAF's Runtime

```bash
curl http://localhost:8000/runtime/modules      # includes "task"
curl http://localhost:8000/runtime/capabilities # includes "task.manage"
curl http://localhost:8000/info                 # "task" listed with status "implemented"
```

## Docs

- [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) — sprint-by-sprint history, the
  TEAF public API journey, and every documented limitation/decision along
  the way.
- [`docs/PROJECT-STRUCTURE.md`](docs/PROJECT-STRUCTURE.md) — directory
  layout and rationale, including the Task Manager module and UI.
- [`docs/RUNNING.md`](docs/RUNNING.md) — install, test, lint, run, and
  endpoint/UI verification instructions.
