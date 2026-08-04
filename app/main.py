"""Reference entrypoint for consuming TEAF's public API.

Written against TEAF v0.6.1-alpha's public `teaf` package (Sprint 2.5.1,
"Public SDK & Packaging"). `Application` takes no `name`/`version`/
`description` arguments — its only parameter is an optional `settings`
override (`teaf.Configuration`). Naming, environment, host, and port are
resolved from the environment (`APP_NAME`, `ENVIRONMENT`, `HOST`, `PORT`
— see .env.example), matching TEAF's own convention. `app.version`
reflects TEAF's own framework version, not this application's — see
`app.config.get_settings().app_version` for this app's own version.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from teaf import Application

app = Application()
