# Running the TEAF Reference App

## Install

TEAF is a sibling checkout, installed first (it isn't published to any
package index, so it's a manual editable install rather than a
`pyproject.toml` dependency — see the note in `pyproject.toml`):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ../torus-enterprise-framework
pip install -e ".[dev]"
cp .env.example .env
```

Built and verified against TEAF `v0.10.0-alpha`.

## Run the tests

```bash
pytest -v
```

All tests run for real against TEAF — `tests/test_config.py` covers this
app's own `app_version` setting, `tests/test_app.py` and `tests/test_ui.py`
exercise the four TEAF endpoints and the UI respectively, and
`tests/modules/task/` covers the Task Manager module layer by layer
(model, repository, service, HTTP routes) plus its SDK registration and
Runtime integration. `tests/conftest.py` provides a session-scoped
`client` fixture — see its docstring for why: TEAF's module bootstrap now
runs during the ASGI lifespan, and re-entering that lifespan twice on the
same `Application` raises "already registered".

Coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## Lint, format, type-check

```bash
ruff check .
black --check .
mypy --strict app tests
```

All three report clean — genuinely, not just "clean in our own files":
`mypy_path` (see `pyproject.toml`) makes all of `teaf/_internal/` visible
for static resolution, and two of TEAF's own provider modules (Redis
cache, LDAP identity) reference third-party client libraries this app
doesn't install (it uses neither feature); those two are the only
`[[tool.mypy.overrides]]` entries, scoped to exactly those two libraries.

## Run the application

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/** in a browser for the Task Manager UI —
see the README for a full click-through description (create, edit,
complete, delete, with loading/empty/error states).

Verify TEAF's own JSON endpoints (unaffected by the UI living at `/` —
see `docs/BOOTSTRAP.md`, "Sprint A1.1", for how the route conflict was
resolved):

```bash
curl http://localhost:8000/health
curl http://localhost:8000/info
curl http://localhost:8000/runtime/info
```

Verify the Task Manager module is registered:

```bash
curl http://localhost:8000/runtime/modules      # "task", status "implemented"
curl http://localhost:8000/runtime/capabilities # "task.manage"
```

Verify the `/tasks` API directly — see the README for the full curl
walkthrough (create, list, get, update, complete, delete).
