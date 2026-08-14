# Changelog

Notable changes to the TEAF Reference App. Versions refer to this
application, not to TEAF — the framework version each release was built
against is stated per entry. `docs/BOOTSTRAP.md` carries the long-form
reasoning behind each sprint; this file is the summary.

## 0.4.0-alpha — Sprint A3

Built against TEAF `v0.10.3-alpha`.

### Added

- **Demo authentication**, built entirely on TEAF's public security API:
  `JWTProvider` (issue / verify / revoke), `Argon2PasswordHasher`,
  `JWTIdentityProvider`, `IdentityProviderRegistry`, `PrincipalResolver`,
  `StaticRoleResolver`, `SecurityMiddleware`, and the `@authorize()`
  decorator. No second authentication mechanism, and no framework change.
- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
- Two demo accounts, hashed with Argon2id at startup from configuration:
  `demo` (read + write) and `viewer` (read only), so `403` is a real
  behaviour of the running app and not just a test fixture.
- **Every `/tasks` endpoint is now protected**: `task.read` for reads,
  `task.write` for writes. Anonymous → `401`; authenticated without the
  permission → `403`.
- **Login screen** (`/login`) and a session bar with sign-out, in the same
  vanilla ES-module frontend — no React, no bundler, no npm.
- `app/static/session.js` — the browser's auth state in one place, stored
  in `sessionStorage` (trade-off documented in that file and the README).
- **Browser end-to-end suite** (`tests/e2e/`, 39 tests) driving real
  Chromium against a real `uvicorn` process, real TEAF middleware, real
  JWTs, and a real SQLite file, on a random port with a temporary
  database. Every assertion goes through the UI.
- `AUTH_JWT_SECRET`, `AUTH_DEMO_USERNAME` / `AUTH_DEMO_PASSWORD`,
  `AUTH_VIEWER_USERNAME` / `AUTH_VIEWER_PASSWORD`, and
  `AUTH_ACCESS_TOKEN_TTL_SECONDS` settings.

### Changed

- `tests/conftest.py`'s `client` fixture is now *unauthenticated*; use
  `user_client` or `viewer_client` for authenticated requests.
- E2E tests are sorted to the end of the run: Playwright's sync API keeps
  an event loop alive that breaks any async test collected after it.

### Fixed

- **The `hidden` attribute did not hide.** `.create-form { display: flex }`
  outranked the user-agent's `[hidden] { display: none }`, so a read-only
  account was shown a create form it could not use. Found by the browser
  suite; invisible to every server-side test.
- The read-only notice was overwritten by "Loading tasks…" a moment after
  it appeared.

### Security

- Passwords are only ever stored and compared as Argon2id hashes.
- A wrong password and an unknown username produce byte-identical
  responses, and both cost a hash — no account-existence oracle by content
  or by timing.
- Logout revokes the token server-side; it does not merely forget it.
- Verified against a `debug`-level log: no password, token, `Authorization`
  header, or signing key is written anywhere.
- No signing key ships with the app — one is generated per process when
  `AUTH_JWT_SECRET` is unset.

### Known limitations

- **This is demonstration authentication, not identity management.** Two
  fixed accounts, no registration, no password reset, no lockout, no
  refresh flow, no audit trail.
- **`sessionStorage`, not an httpOnly cookie.** Readable by same-origin
  script; mitigated by a strict `default-src 'self'` CSP with no inline
  scripts. Production identity should use an httpOnly, SameSite cookie
  plus CSRF protection.
- **`POST`/`PUT`/`PATCH` with a malformed body answer `422` before `401`.**
  FastAPI validates the schema before the endpoint's decorator runs. No
  data is disclosed, and the schema is already public in the OpenAPI
  document; with a well-formed body an anonymous request is always `401`.
- TEAF's own `/health`, `/info`, and `/runtime/*` remain public.

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
