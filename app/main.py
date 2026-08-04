"""Reference entrypoint for consuming TEAF's public API.

Written against TEAF v0.6.2-alpha's public `teaf` package. `Application`
takes no `name`/`version`/`description` arguments — its only parameter is
an optional `settings` override (`teaf.Configuration`). Naming,
environment, host, and port are resolved from the environment
(`APP_NAME`, `ENVIRONMENT`, `HOST`, `PORT` — see .env.example), matching
TEAF's own convention. `app.version` reflects TEAF's own framework
version, not this application's — see `app.config.get_settings().app_version`
for this app's own version.

Registers the Task Manager business module (app/modules/task/) against
this Application's `Runtime`. TEAF's `create_app()` wires FastAPI's
`lifespan` directly to `Runtime.startup()`/`shutdown()` (see
docs/BOOTSTRAP.md, "Sprint A1"), which replaces Starlette's on_startup
event mechanism entirely — so a module cannot hook into that lifespan
after the fact via `add_event_handler`. The only public way to have a
module registered *before* `Runtime.startup()` runs is to bootstrap it
here, before uvicorn's event loop takes over.

`module.bootstrap()` is `async`, but this module-level code runs
synchronously at import time — and, under `uvicorn app.main:app`,
that import happens *inside* uvicorn's own already-running event loop
(uvloop), so a plain `asyncio.run()` here raises "cannot be called from
a running event loop". Running the bootstrap on a dedicated thread (with
its own fresh loop) and joining it sidesteps that without depending on
whether an outer loop happens to be running.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import asyncio
import threading
from typing import cast

from teaf import Application, ModuleContext

from app.modules.task.module import TaskModule
from app.modules.task.routes import create_task_router
from app.modules.task.services import TaskService

app = Application()

_task_module = TaskModule()
_context = ModuleContext(runtime=app.runtime, module_id="task")
_bootstrap_thread = threading.Thread(target=lambda: asyncio.run(_task_module.bootstrap(_context)))
_bootstrap_thread.start()
_bootstrap_thread.join()

_task_service = cast(TaskService, app.runtime.resolve_service(TaskService))
app.asgi.include_router(create_task_router(_task_service))
