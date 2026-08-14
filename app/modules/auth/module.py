"""AuthModule — registers demo authentication against a TEAF Runtime.

Registered through the same public Module SDK as the Task module, so
authentication shows up in `/runtime/modules` and `/runtime/capabilities`
like any other business capability rather than being bolted onto the app
outside the framework's view.

The security components themselves (`JWTProvider`, the identity provider
registry, the principal resolver) are built in `security.py` and passed
in, because `app/main.py` also needs the registry and resolver to install
`SecurityMiddleware` — and the middleware has to be added to the ASGI app
at import time, before the module lifecycle runs.
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

from app.modules.auth.security import SecurityComponents
from app.modules.auth.services import AuthService


class AuthModule(Module):
    """Demo authentication: two fixed accounts, JWT tokens, role-based access."""

    def __init__(self, components: SecurityComponents) -> None:
        # See TaskModule for why `super().__init__()` is not optional.
        super().__init__()
        self._components = components

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="auth", name="auth", display_name="Demo Authentication")
            .with_version("0.4.0-alpha")
            .with_description(
                "Demonstration login built on TEAF's public security API. Not identity management."
            )
            .with_category(ModuleCategory.GENERIC)
            .add_service(
                AuthService,
                lambda _container: self._components.auth_service,
                lifetime=Lifetime.SINGLETON,
            )
            .add_capability(
                id="auth.demo-login",
                name="auth-demo-login",
                category=CapabilityCategory.SECURITY,
                description="Username/password login issuing revocable JWT access tokens.",
            )
            .add_healthcheck(name="auth.ping", check=lambda: Health.HEALTHY)
            .build()
        )

    async def ready(self, context: ModuleContext) -> None:
        # Same reason as TaskModule: build the singleton while startup is
        # still single-threaded, so two concurrent first requests cannot
        # both enter the factory. See docs/BOOTSTRAP.md, "Sprint A2".
        context.runtime.resolve_service(AuthService)
        context.logger.info("auth_module_ready")
