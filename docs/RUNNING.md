# Running the TEAF Reference App

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

This installs cleanly today — `teaf` is intentionally **not** declared as
a dependency (it cannot be resolved yet; see `docs/BOOTSTRAP.md`), so it
does not block this step.

## Run the tests

```bash
pytest -v
```

Expected result today:

- `tests/test_config.py` — all tests **pass** (no TEAF dependency).
- `tests/test_app.py` — all tests **skip**, with reason
  `"TEAF does not yet expose a public teaf package — see docs/BOOTSTRAP.md."`

Coverage:

```bash
pytest --cov=backend --cov-report=term-missing
```

## Lint, format, type-check

```bash
ruff check .
black --check .
mypy --strict backend tests
```

`ruff` and `black` report clean. `mypy --strict` reports exactly **one**
error — an unresolved `teaf` import in `backend/app.py` — which is the
documented, expected signature of the TEAF limitation described in
`docs/BOOTSTRAP.md`, not a defect in this codebase.

## Run the application (not yet functional)

Once TEAF ships a public `teaf` package with an `Application` class (see
`docs/BOOTSTRAP.md`), this application starts with:

```bash
uvicorn backend.app:app --reload
```

And the four TEAF endpoints can be verified with:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/info
curl http://localhost:8000/runtime/info
```

Today, running the above will fail at import time with
`ModuleNotFoundError: No module named 'teaf'` — this is expected and
documented, not a bug in this repository.
