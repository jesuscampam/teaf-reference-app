# TEAF Reference App

Official reference application for the Torus Enterprise Application
Framework (TEAF). Version `0.4.0-alpha`, built against TEAF
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

Since Sprint A3 it also proves **authenticated access**: a login screen, a
protected API, role-based `403`s, and server-side logout, all built on
TEAF's public security API (`JWTProvider`, `SecurityMiddleware`,
`@authorize`, `Argon2PasswordHasher`) without a line of framework change.
It remains a *demonstration* login, not identity management — see
"Authentication" below.

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

Open **http://localhost:8000/** in a browser. You will be sent to
**/login** — sign in with `demo` / `demo1234` (or `viewer` / `viewer1234`
for a read-only account). Tasks are written to `tasks.db` in the working
directory (override with `TASK_DATABASE_PATH`) and are still there after a
restart.

## Authentication

> **This is demonstration authentication, not identity management.** Two
> fixed accounts created at startup from configuration, no registration, no
> password reset, no lockout, no refresh flow, no audit trail. It exists to
> show TEAF's security API working end to end.

| Account | Password | Can |
|---|---|---|
| `demo` | `demo1234` | read and change tasks (`task.read`, `task.write`) |
| `viewer` | `viewer1234` | read only — changing a task returns `403` |

Both are overridable (`AUTH_DEMO_USERNAME`, `AUTH_DEMO_PASSWORD`, …) and
neither password is ever stored: they are hashed with Argon2id at startup.

### How it works

```
POST /auth/login  ->  Argon2 verify  ->  JWTProvider.issue  ->  access token
        |
browser stores it in sessionStorage (see app/static/session.js)
        |
httpClient.js attaches `Authorization: Bearer …` to every request
        |
SecurityMiddleware resolves it into a Principal on the request context
        |
@authorize(permission=…) on each endpoint  ->  200 / 401 / 403
        |
POST /auth/logout  ->  JWTProvider.revoke  ->  the token stops verifying
```

Logout is server-side: the token is revoked, not merely forgotten by the
browser.

### Endpoints

| Method | Path | Auth |
|---|---|---|
| `POST` | `/auth/login` | public |
| `POST` | `/auth/logout` | token required; revokes it |
| `GET` | `/auth/me` | token required; used to restore a session |

### Signing key

`AUTH_JWT_SECRET` is **empty by default and no secret ships with the app** —
an unset value makes it generate a random HS256 key per process, so there
is no default anybody could forge a token against. The visible cost: every
restart invalidates outstanding tokens. Set it to keep sessions alive
(TEAF rejects anything under 32 bytes, RFC 7518 §3.2):

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Where the token is kept, and why

`sessionStorage`. The honest trade-off:

| | XSS-readable | Survives tab close | Needs CSRF defence |
|---|---|---|---|
| httpOnly cookie | no | yes | yes |
| `localStorage` | yes | yes | no |
| `sessionStorage` ← this app | yes | no | no |

`sessionStorage` is readable by same-origin script, which is acceptable
here because the page ships a strict `default-src 'self'` CSP with no
inline scripts and no external origins, and the token dies with the tab.
**An application handling real accounts should use an httpOnly, SameSite
cookie with CSRF protection instead.**

## Test

```bash
pytest                      # everything: unit, integration, and browser E2E
pytest --ignore=tests/e2e   # skip the browser suite
pytest tests/e2e            # only the browser suite
```

The E2E tests drive real Chromium against a real `uvicorn` process on a
random port with a temporary database. They skip cleanly if Playwright's
browser is not installed, so a machine without one still runs everything
else. To install it: `playwright install chromium`.

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

Every `/tasks` endpoint needs a token, so start by getting one:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo1234"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Without it, everything is 401:
curl -i http://localhost:8000/tasks | head -1     # HTTP/1.1 401 Unauthorized
```

```bash
# Create
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk", "description": "2% milk, one gallon"}'

# List
curl http://localhost:8000/tasks -H "Authorization: Bearer $TOKEN"

# Get one (replace <id> with the id from the create response)
curl http://localhost:8000/tasks/<id> -H "Authorization: Bearer $TOKEN"

# Update
curl -X PUT http://localhost:8000/tasks/<id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy oat milk", "description": "unsweetened"}'

# Move between states
curl -X PATCH http://localhost:8000/tasks/<id>/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "IN_PROGRESS"}'

# Complete (shorthand for status DONE)
curl -X POST http://localhost:8000/tasks/<id>/complete -H "Authorization: Bearer $TOKEN"

# Counts per status
curl http://localhost:8000/tasks/stats -H "Authorization: Bearer $TOKEN"

# Delete
curl -X DELETE http://localhost:8000/tasks/<id> -H "Authorization: Bearer $TOKEN"
```

A read-only account gets `403` on any of the write calls:

```bash
VIEWER=$(curl -s -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "viewer", "password": "viewer1234"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -o /dev/null -w "%{http_code}\\n" http://localhost:8000/tasks -H "Authorization: Bearer $VIEWER"          # 200
curl -s -o /dev/null -w "%{http_code}\\n" -X DELETE http://localhost:8000/tasks/<id> -H "Authorization: Bearer $VIEWER"  # 403
```

### Verify persistence

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Survives", "description": "restart me"}'

# Stop the server (Ctrl-C), start it again, log in again, then:
curl http://localhost:8000/tasks -H "Authorization: Bearer $TOKEN"

# Note: with AUTH_JWT_SECRET unset the key is regenerated on restart, so
# the old token no longer verifies — log in again to get a fresh one. The
# *tasks* survive regardless; that is the point of this check.
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
| `APP_VERSION` | `0.4.0-alpha` | This app's version, distinct from TEAF's |
| `TASK_DATABASE_PATH` | `tasks.db` | SQLite file; `:memory:` for a throwaway database |

`app/config.py` declares only the last two. The rest already belong to
TEAF's public `Configuration`, and redeclaring them would duplicate the
framework.

## Known limitations

- **Demo authentication only** — see the box above.
- **`sessionStorage`, not an httpOnly cookie** — trade-off table above.
- **A malformed body answers `422` before `401`.** FastAPI validates the
  request schema before the endpoint's `@authorize` decorator runs, so an
  anonymous `POST /tasks` with an invalid body is rejected as `422`. No
  data is disclosed and the schema is already public in the OpenAPI
  document; with a well-formed body, an anonymous request is always `401`.
- **TEAF's own endpoints stay public**: `/health`, `/info`, `/runtime/*`.
  Protecting them was never in scope, and a monitor needs `/health`.
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
