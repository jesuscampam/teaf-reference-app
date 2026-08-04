# TEAF Reference App

Official reference application for the Torus Enterprise Application
Framework (TEAF). Version `0.2.0-alpha`, built against TEAF `v0.6.2-alpha`.

## What this is

A minimal application demonstrating correct consumption of TEAF's public
API. It bootstraps via `from teaf import Application`, and — as of Sprint
A1 — includes one real business module, **Task Manager**, built entirely
against TEAF's public Module SDK (`teaf.Module`, `ModuleBuilder`,
`ModuleContext`) with no database, auth, or business logic beyond simple
CRUD on a `Task` entity. See [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) for
the full scope and sprint-by-sprint history.

## Install

```bash
pip install -e ../torus-enterprise-framework
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest -v
```

## Task Manager module

The reference module for authoring TEAF business modules: one entity
(`Task`: `id`, `title`, `description`, `completed`, `created_at`,
`updated_at`), one in-memory repository (no database), one service
(`TaskService`), and six HTTP endpoints. See
[`docs/PROJECT-STRUCTURE.md`](docs/PROJECT-STRUCTURE.md) for the module's
internal layout and [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) ("Sprint
A1") for how it registers against TEAF's `Runtime` using only public API.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/tasks` | List all tasks |
| `GET` | `/tasks/{id}` | Get one task |
| `POST` | `/tasks` | Create a task |
| `PUT` | `/tasks/{id}` | Update a task |
| `DELETE` | `/tasks/{id}` | Delete a task |
| `POST` | `/tasks/{id}/complete` | Mark a task as completed |

### Try it

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
  layout and rationale, including the Task Manager module's internals.
- [`docs/RUNNING.md`](docs/RUNNING.md) — install, test, lint, run, and
  endpoint verification instructions.
