# Project Structure

```
teaf-reference-app/
├── app/
│   ├── __init__.py
│   ├── config.py      # This app's own settings: only `app_version`
│   └── main.py         # from teaf import Application → app = Application()
├── tests/
│   ├── __init__.py
│   ├── test_config.py  # app/config.py — no TEAF dependency
│   └── test_app.py     # Application instantiation + the 4 TEAF endpoints
├── docs/
│   ├── BOOTSTRAP.md          # Sprint scope, the TEAF public API history, and the app/ rename rationale
│   ├── PROJECT-STRUCTURE.md  # This file
│   └── RUNNING.md            # Install / test / lint / run instructions
├── README.md
├── pyproject.toml
├── .gitignore
└── .env.example
```

## Rationale

- **`app/`** (not `backend/` — see `docs/BOOTSTRAP.md`, "Why `app/`, not
  `backend/`") holds only what this reference app owns: its own
  configuration and the single entrypoint that consumes TEAF's public
  API. No routers, no models, no services — TEAF provides all of that.
- **`config.py`** is separated from **`main.py`** so the parts of this
  application that don't depend on TEAF (its own version string) stay
  independently testable. It intentionally does **not** redeclare
  `app_name`/`environment`/`host`/`port` — TEAF's own public
  `Configuration`/`get_configuration` already cover those, reading the
  same environment variables.
- **`tests/`** mirrors `app/` one-to-one: one test module per source
  module, no shared fixtures beyond what `pytest` and `pytest-cov`
  provide out of the box.
- **`docs/`** is kept to exactly the three files this sprint calls for —
  no extra documents, per the "don't add more than requested" spirit of
  this sprint.
