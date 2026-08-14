"""TaskModule — registers the Task Manager module against a TEAF Runtime.

Built entirely against TEAF's public SDK facade (`teaf.Module`,
`ModuleBuilder`, `ModuleContext`, `ModuleManifest`, `Lifetime`,
`CapabilityCategory`, `Health`) — no `teaf._internal.*` import anywhere,
matching the pattern demonstrated in TEAF's own
`examples/basic-module/main.py`.

The module owns two pieces of wiring worth pointing at:

**The event bus.** `TaskService` publishes application events (see
`events.py`) onto the bus TEAF already runs, reached through the public
`ModuleContext.events`. The bus is captured in the `configure` hook,
which `ModuleBase.bootstrap` runs *before* it binds services — so by the
time the container can build a `TaskService`, the bus is there. The
service factory reads it through `self._event_bus` rather than closing
over a value captured at manifest time, because `get_manifest()` receives
no context and therefore has no bus to close over.

**The repository.** `SqliteTaskRepository` is a singleton for the life of
the runtime, holding one connection; `dispose` closes it so a shut-down
application leaves no open file handle behind.
"""

from __future__ import annotations

from teaf import (
    CapabilityCategory,
    EventBus,
    Health,
    Lifetime,
    Module,
    ModuleBuilder,
    ModuleCategory,
    ModuleContext,
    ModuleManifest,
)

from app.config import get_settings
from app.modules.task.repository import SqliteTaskRepository, TaskRepository
from app.modules.task.services import TaskService


class TaskModule(Module):
    """The Task Manager business module: one entity, one service, SQLite-backed."""

    def __init__(self, database_path: str | None = None) -> None:
        # `ModuleBase.__init__` builds the lifecycle state machine TEAF's
        # own bootstrap drives — skipping it fails later with a bare
        # AttributeError on `self.lifecycle`.
        super().__init__()
        #: Overridable so tests can point the module at a throwaway
        #: database without touching process-wide settings.
        self._database_path = database_path or get_settings().task_database_path
        self._event_bus: EventBus | None = None
        self._repository: SqliteTaskRepository | None = None

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="task", name="task", display_name="Task Manager")
            .with_version("0.4.0-alpha")
            .with_description("Minimal task-tracking module validating TEAF's public Module SDK.")
            .with_category(ModuleCategory.GENERIC)
            .add_service(TaskRepository, self._build_repository, lifetime=Lifetime.SINGLETON)
            .add_service(
                TaskService,
                # TaskRepository is a Protocol, used here only as a DI key —
                # mypy's type-abstract check assumes type[T] args must be
                # instantiable, which doesn't apply to container lookups.
                lambda c: TaskService(c.resolve(TaskRepository), self._event_bus),  # type: ignore[type-abstract]
                lifetime=Lifetime.SINGLETON,
            )
            .add_capability(
                id="task.manage",
                name="task-manage",
                category=CapabilityCategory.UTILITY,
                description="Create, read, update, delete, and re-state tasks.",
            )
            .add_healthcheck(name="task.ping", check=lambda: Health.HEALTHY)
            .build()
        )

    def configure(self, context: ModuleContext) -> None:
        """Capture the runtime's event bus before any service is built."""
        self._event_bus = context.events

    async def ready(self, context: ModuleContext) -> None:
        # Build the singletons now, while bootstrap is still single-threaded.
        #
        # Not an optimisation — it avoids a real failure. Starlette runs sync
        # handlers in a thread pool, so two requests arriving together (this
        # UI loads `/tasks` and `/tasks/stats` in parallel) can both be the
        # *first* to resolve `TaskService`. TEAF's container tracks its
        # in-flight resolution chain in state shared across threads, so the
        # second thread sees `TaskService -> TaskRepository -> TaskService`
        # and raises `CircularDependencyException` — a false positive; the
        # graph has no cycle. Resolving once here means every later request
        # gets the cached singleton and never re-enters the factory.
        #
        # This is a TEAF defect, reported rather than patched (the framework
        # is not modified from this repository). See docs/BOOTSTRAP.md,
        # "Sprint A2", "Concurrent first resolution of a singleton".
        context.runtime.resolve_service(TaskService)
        context.logger.info("task_module_ready")

    async def dispose(self, context: ModuleContext) -> None:
        if self._repository is not None:
            self._repository.close()
            self._repository = None

    def _build_repository(self, _container: object) -> SqliteTaskRepository:
        self._repository = SqliteTaskRepository(self._database_path)
        return self._repository
