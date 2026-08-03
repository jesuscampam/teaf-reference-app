# Project Structure

```
teaf-reference-app/
├── backend/
│   ├── __init__.py
│   ├── config.py     # App-level settings (APP_NAME, APP_VERSION, ENVIRONMENT, HOST, PORT)
│   └── app.py         # from teaf import Application → app = Application(...)
├── tests/
│   ├── __init__.py
│   ├── test_config.py # Passes today — no TEAF dependency
│   └── test_app.py    # Skips today — guarded by pytest.importorskip("teaf")
├── docs/
│   ├── BOOTSTRAP.md          # Sprint scope + TEAF limitation report
│   ├── PROJECT-STRUCTURE.md  # This file
│   └── RUNNING.md            # Install / test / lint / run instructions
├── README.md
├── pyproject.toml
├── .gitignore
└── .env.example
```

## Rationale

- **`backend/`** holds only what this reference app owns: its own
  configuration and the single entrypoint that consumes TEAF's public
  API. No routers, no models, no services — TEAF provides all of that.
- **`config.py`** is separated from **`app.py`** so the parts of this
  application that don't depend on TEAF (configuration) can be built,
  typed, and tested independently of TEAF's release state.
- **`tests/`** mirrors `backend/` one-to-one: one test module per source
  module, no shared fixtures beyond what `pytest` and `pytest-cov`
  provide out of the box.
- **`docs/`** is kept to exactly the three files this sprint calls for —
  no extra documents, per the "don't add more than requested" spirit of
  this sprint.
