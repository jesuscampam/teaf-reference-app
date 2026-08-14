"""Reference entrypoint for consuming TEAF's public API.

Written against TEAF v0.10.0-alpha's public `teaf` package. `Application`
takes no `name`/`version`/`description` arguments — its only positional
parameter is an optional `settings` override (`teaf.Configuration`).
Naming, environment, host, and port are resolved from the environment
(`APP_NAME`, `ENVIRONMENT`, `HOST`, `PORT` — see .env.example), matching
TEAF's own convention. `app.version` reflects TEAF's own framework
version, not this application's — see `app.config.get_settings().app_version`
for this app's own version.

Registers the Task Manager business module (app/modules/task/) via
TEAF's Module Registration API (Sprint 2.6.3): `Application(modules=[...])`
starts each module automatically as part of TEAF's own ASGI lifespan, in
the same async context that already drives `Runtime.startup()`/
`shutdown()`. This replaced the thread + `asyncio.run()` workaround this
app used against TEAF v0.6.2-alpha — see docs/BOOTSTRAP.md, "Sprint
A1.1", for why that workaround existed and why it's no longer needed.

Because module bootstrap now happens *during* the ASGI lifespan rather
than eagerly at import time, `TaskService` isn't resolvable the moment
`Application(...)` returns — only once the lifespan has actually started
(a real `uvicorn` request, or `with TestClient(app):` in tests). Routes
that need it resolve it lazily, per call, via `app.runtime` — see
`app/modules/task/routes.py`.

Serves the Task Manager UI (app/static/) at `GET /`. TEAF's own
`create_app()` already registers a `GET /` JSON status route (from its
health router) before this module ever gets `.asgi` — Starlette matches
the first full (path, method) match in registration order, so without
reordering, our handler below would be permanently unreachable. The
one-line reorder below affects only the exact `/` route; `/health`,
`/info`, `/runtime/*`, and `/tasks/*` are untouched. (No `Mount("/", ...)`
for static assets — that would shadow every other route, since Starlette
treats a mount at `/` as a catch-all — assets are served under `/static`
instead, which needs no reordering.)

TEAF's own `SecurityHeadersMiddleware` (Sprint 2.9.2) sends
`Content-Security-Policy: default-src 'none'` on every response by
default — correct for a pure JSON API, but it silently blocks a browser
from loading `/static/styles.css`/`/static/app.js` or calling `fetch()`
against `/tasks` from a page served under that policy (caught only by
actually loading the UI in a real browser — curl doesn't enforce CSP).
Per that middleware's own documented contract ("a header the application
already sets is never overwritten"), setting our own
`Content-Security-Policy` on the `/` response is the public, sanctioned
override — no TEAF internals touched, no workaround.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from teaf import Application, SecurityMiddleware

from app.config import get_settings
from app.modules.auth.module import AuthModule
from app.modules.auth.routes import create_auth_router
from app.modules.auth.security import build_security
from app.modules.auth.services import AuthService
from app.modules.task.module import TaskModule
from app.modules.task.routes import create_task_router
from app.modules.task.services import TaskService

STATIC_DIR = Path(__file__).parent / "static"

#: Same-origin only — this UI loads no external scripts/styles/fonts and
#: makes no cross-origin requests. See module docstring: overrides TEAF's
#: default `default-src 'none'` for this one response only.
_UI_CONTENT_SECURITY_POLICY = "default-src 'self'; frame-ancestors 'none'"

#: Built before `Application` because `SecurityMiddleware` needs the
#: identity registry and principal resolver at import time, while
#: `AuthModule` needs the same components to register `AuthService`.
_SECURITY = build_security(get_settings())

app = Application(modules=[TaskModule(), AuthModule(_SECURITY)])

#: Populates each request's security context from the `Authorization`
#: header. It authenticates but never rejects — an absent or invalid token
#: yields an anonymous context and the request proceeds. Enforcement is
#: `@authorize(...)` on the endpoints themselves, which is the only place
#: that knows which routes are public.
app.asgi.add_middleware(
    SecurityMiddleware,
    provider_registry=_SECURITY.provider_registry,
    principal_resolver=_SECURITY.principal_resolver,
)


def _resolve_task_service() -> TaskService:
    return cast(TaskService, app.runtime.resolve_service(TaskService))


def _resolve_auth_service() -> AuthService:
    return cast(AuthService, app.runtime.resolve_service(AuthService))


app.asgi.include_router(create_task_router(_resolve_task_service))
app.asgi.include_router(create_auth_router(_resolve_auth_service))


@app.asgi.get("/", include_in_schema=False)
def serve_ui() -> FileResponse:
    """The task application. Public to serve, but useless without a token:
    its first request is `GET /auth/me`, and a 401 sends the browser to
    `/login`. Gating the HTML itself would need a cookie, which this app
    deliberately does not use — see docs/BOOTSTRAP.md, "Sprint A3"."""
    return _page("index.html")


@app.asgi.get("/login", include_in_schema=False)
def serve_login() -> FileResponse:
    """The login page. Genuinely public."""
    return _page("login.html")


def _page(filename: str) -> FileResponse:
    return FileResponse(
        STATIC_DIR / filename,
        headers={"Content-Security-Policy": _UI_CONTENT_SECURITY_POLICY},
    )


def _route_index(endpoint: object) -> int:
    """Position of the route serving `endpoint`, by identity.

    Sprint A1.1 popped the last-registered route instead, which was the
    same thing back when `/` was registered last. It no longer is —
    `/login` follows it — so the route is now located explicitly rather
    than by position.
    """
    for index, route in enumerate(app.asgi.router.routes):
        if getattr(route, "endpoint", None) is endpoint:
            return index
    raise RuntimeError("UI route not found — cannot order it ahead of TEAF's own '/'")


# Move `/` ahead of TEAF's own `/` JSON status route (see module
# docstring). `/login` needs no reorder — nothing else claims that path.
app.asgi.router.routes.insert(0, app.asgi.router.routes.pop(_route_index(serve_ui)))

app.asgi.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
