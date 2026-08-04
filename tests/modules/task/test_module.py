"""Tests for app.modules.task.module.TaskModule — registration via TEAF's public SDK.

Uses a standalone `teaf.Runtime`, the same pattern demonstrated in TEAF's
own `examples/basic-module/main.py` — no internal namespace imports.
"""

from __future__ import annotations

import asyncio

from teaf import ModuleContext, ModuleRegistry, Runtime

from app.modules.task.module import TaskModule
from app.modules.task.services import TaskService


def test_manifest_is_valid() -> None:
    manifest = TaskModule().get_manifest()

    assert manifest.descriptor.id == "task"
    assert manifest.descriptor.version == "0.2.0-alpha"
    assert {capability.id for capability in manifest.capabilities} == {"task.manage"}


def test_bootstrap_registers_module_and_service() -> None:
    runtime = Runtime(registry=ModuleRegistry(), framework_version="0.6.2-alpha")
    module = TaskModule()

    asyncio.run(module.bootstrap(ModuleContext(runtime=runtime, module_id="task")))

    assert any(descriptor.name == "task" for descriptor in runtime.modules)
    service = runtime.resolve_service(TaskService)
    assert isinstance(service, TaskService)
