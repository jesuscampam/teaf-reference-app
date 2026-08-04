"""TaskModule — registers the Task Manager module against a TEAF Runtime.

Built entirely against TEAF's public SDK facade (`teaf.Module`,
`ModuleBuilder`, `ModuleContext`, `ModuleManifest`, `Lifetime`,
`CapabilityCategory`, `Health`) — no `teaf._internal.*` import anywhere,
matching the pattern demonstrated in TEAF's own
`examples/basic-module/main.py`.
"""

from __future__ import annotations

from teaf import (
    CapabilityCategory,
    Health,
    Lifetime,
    Module,
    ModuleBuilder,
    ModuleCategory,
    ModuleContext,
    ModuleManifest,
)

from app.modules.task.repository import InMemoryTaskRepository, TaskRepository
from app.modules.task.services import TaskService


class TaskModule(Module):
    """The Task Manager business module: one entity, one service, in-memory only."""

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="task", name="task", display_name="Task Manager")
            .with_version("0.2.0-alpha")
            .with_description("Minimal task-tracking module validating TEAF's public Module SDK.")
            .with_category(ModuleCategory.GENERIC)
            .add_service(
                TaskRepository, lambda c: InMemoryTaskRepository(), lifetime=Lifetime.SINGLETON
            )
            .add_service(
                TaskService,
                # TaskRepository is a Protocol, used here only as a DI key —
                # mypy's type-abstract check assumes type[T] args must be
                # instantiable, which doesn't apply to container lookups.
                lambda c: TaskService(c.resolve(TaskRepository)),  # type: ignore[type-abstract]
                lifetime=Lifetime.SINGLETON,
            )
            .add_capability(
                id="task.manage",
                name="task-manage",
                category=CapabilityCategory.UTILITY,
                description="Create, read, update, delete, and complete tasks.",
            )
            .add_healthcheck(name="task.ping", check=lambda: Health.HEALTHY)
            .build()
        )

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info("task_module_ready")
