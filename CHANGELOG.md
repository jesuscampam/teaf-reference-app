# Changelog

Notable changes to the TEAF Reference App. Versions refer to this
application, not to TEAF — the framework version each release was built
against is stated per entry. `docs/BOOTSTRAP.md` carries the long-form
reasoning behind each sprint; this file is the summary.

## 0.3.0-alpha — Sprint A2

Built against TEAF `v0.10.3-alpha`.

### Added

- **Persistence.** `SqliteTaskRepository` (standard-library `sqlite3`, no
  new dependency) replaces in-memory storage in the running application.
  Tasks survive a restart. Path configurable via `TASK_DATABASE_PATH`;
  `InMemoryTaskRepository` is kept for unit tests.
- **Application events** on TEAF's own bus, reached through the public
  `ModuleContext.events`: `task.created`, `task.updated`,
  `task.status_changed`, `task.deleted` (`app/modules/task/events.py`).
- **Three-state task status** — `TODO`, `IN_PROGRESS`, `DONE` —
  replacing the previous `completed` boolean.
- `PATCH /tasks/{id}/status` for arbitrary transitions, and
  `GET /tasks/stats` for the UI's counters.
- Domain validation in `TaskService` (blank and over-long titles and
  descriptions), surfaced as `400`; status conflicts as `409`.
- `app/static/httpClient.js` — a shared API client. No component calls
  `fetch` directly any more. Native ES modules; still no bundler, npm, or
  Node.
- UI: status badges, per-row status advance, and a counter row fed by
  `GET /tasks/stats`.
- `tests/test_public_api.py` — asserts the app starts through
  `from teaf import Application` and AST-scans every source file for
  `teaf._internal` / `backend.*` imports, with a test proving the
  detector actually detects.
- This changelog.

### Changed

- `TaskResponse` exposes `status` instead of `completed`. **Breaking** for
  API clients written against 0.2.0-alpha.
- `POST /tasks/{id}/complete` is kept (it sets `DONE`) but now returns
  `409` when the task is already done, instead of silently succeeding.
- `TaskModule` resolves its services during `ready()` rather than leaving
  the first request to do it — see "Fixed".

### Fixed

- **False `CircularDependencyException` under concurrent load.** Two
  requests arriving together could both be the first to resolve
  `TaskService`; TEAF's container tracks its in-flight resolution chain in
  state shared across threads and reported
  `TaskService -> TaskRepository -> TaskService` — a cycle that does not
  exist. Surfaced by the UI loading `/tasks` and `/tasks/stats` in
  parallel. Resolved application-side by constructing the singletons
  during bootstrap, while startup is still single-threaded. **The
  framework was not modified**; the defect is reported in
  `docs/BOOTSTRAP.md`.

### Known limitations

- **No authentication.** TEAF exposes a full public security surface
  (`JWTProvider`, `SecurityMiddleware`, `ApiProtectionModule`), but none of
  it is wired up here; every endpoint is open. Deferred to its own sprint.
- **No migration framework.** Schema creation is one idempotent
  `CREATE TABLE IF NOT EXISTS`.
- **No JavaScript test runner.** The UI is covered by server-side tests
  plus a manual browser click-through, not by unit tests of the JS.

## 0.2.0-alpha — Sprints A1 and A1.1

Built against TEAF `v0.10.0-alpha`.

- Task Manager module registered through TEAF's public Module SDK, with
  six `/tasks` endpoints and in-memory storage.
- Browser UI at `/` (plain HTML, CSS, vanilla JS).
- Adopted `Application(modules=[...])`, removing the
  thread + `asyncio.run()` workaround the app carried against
  v0.6.2-alpha.

## 0.1.1-alpha — Sprint A0.1

- First running application: `uvicorn app.main:app` serving TEAF's four
  built-in endpoints.

## 0.1.0-alpha — Sprint A0

- Repository bootstrap. At the time, TEAF exposed no installable `teaf`
  package; the limitation was documented rather than worked around.
