"""Tests for app.modules.task.module.TaskModule — registration via TEAF's public SDK.

Uses a standalone `teaf.Runtime`, the same pattern demonstrated in TEAF's
own `examples/basic-module/main.py` — no internal namespace imports.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from teaf import EventBus, ModuleContext, ModuleRegistry, Runtime, Version

from app.modules.task.events import TASK_EVENT_NAMES
from app.modules.task.module import TaskModule
from app.modules.task.services import TaskService


def _bootstrapped(module: TaskModule) -> Runtime:
    runtime = Runtime(registry=ModuleRegistry(), framework_version=Version.framework)
    asyncio.run(module.bootstrap(ModuleContext(runtime=runtime, module_id="task")))
    return runtime


def test_manifest_is_valid() -> None:
    manifest = TaskModule(database_path=":memory:").get_manifest()

    assert manifest.descriptor.id == "task"
    assert manifest.descriptor.version == "0.3.0-alpha"
    assert {capability.id for capability in manifest.capabilities} == {"task.manage"}


def test_bootstrap_registers_module_and_service() -> None:
    runtime = _bootstrapped(TaskModule(database_path=":memory:"))

    assert any(descriptor.name == "task" for descriptor in runtime.modules)
    service = runtime.resolve_service(TaskService)
    assert isinstance(service, TaskService)


def test_bootstrapped_service_publishes_onto_the_runtime_event_bus() -> None:
    """The wiring this module exists to demonstrate: an application's own
    events land on the bus TEAF already runs, reached only through the
    public `ModuleContext.events`.

    The bus is shared, not ours — TEAF publishes its own lifecycle events
    (`module.registered`, `service.resolved`, …) onto it too, so the
    application's events are filtered out of the full history rather than
    compared against it.
    """
    runtime = _bootstrapped(TaskModule(database_path=":memory:"))
    service = runtime.resolve_service(TaskService)
    assert isinstance(service, TaskService)

    service.create_task(title="wired", description="through the runtime bus")

    bus = runtime.event_bus
    assert isinstance(bus, EventBus)
    history = bus.history()
    assert [event.name for event in history if event.name in TASK_EVENT_NAMES] == ["task.created"]
    # The framework's own events share the bus — that's the point.
    assert any(event.name.startswith("module.") for event in history)


def test_module_persists_to_the_database_path_it_was_given(tmp_path: Path) -> None:
    database = tmp_path / "given.db"
    runtime = _bootstrapped(TaskModule(database_path=str(database)))
    service = runtime.resolve_service(TaskService)
    assert isinstance(service, TaskService)

    service.create_task(title="on disk", description="in the given file")

    assert database.exists()


def test_services_are_resolved_during_bootstrap(tmp_path: Path) -> None:
    """Regression guard for a concurrency failure, not a style preference.

    If the singleton is first built by a request instead of by bootstrap,
    two requests arriving together both enter the factory and TEAF's
    container reports a false `CircularDependencyException` (see the
    comment on `TaskModule.ready`). Bootstrap must leave the service
    already constructed — proven here by the repository existing before
    any request has been served.
    """
    module = TaskModule(database_path=str(tmp_path / "eager.db"))

    _bootstrapped(module)

    assert module._repository is not None


def test_dispose_closes_the_repository_connection(tmp_path: Path) -> None:
    """A shut-down application must not leave the database file open."""
    module = TaskModule(database_path=str(tmp_path / "disposed.db"))
    runtime = _bootstrapped(module)
    runtime.resolve_service(TaskService)

    asyncio.run(module.dispose(ModuleContext(runtime=runtime, module_id="task")))

    assert module._repository is None
