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

## Run the tests

```bash
pytest -v
```

All tests run for real against TEAF — `tests/test_config.py` covers this
app's own `app_version` setting, and `tests/test_app.py` instantiates
`Application` and exercises the four TEAF endpoints through `TestClient`.

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

All three report clean.

## Run the application

```bash
uvicorn app.main:app --reload
```

Verify the four TEAF endpoints (all served by TEAF itself — this app
defines no routes of its own):

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/info
curl http://localhost:8000/runtime/info
```
