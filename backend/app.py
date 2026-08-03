"""Reference entrypoint for consuming TEAF's public API.

KNOWN LIMITATION — see docs/BOOTSTRAP.md ("TEAF Public API Limitation")
for the full report: as of TEAF v0.5.0-alpha, the framework does not
expose an installable `teaf` package or an `Application` class. This
module is written exactly as the target public API is meant to look —
it is intentionally left unmodified (no workarounds, no internal
`backend.*`/`runtime.*`/etc. imports) so it activates as-is the moment
TEAF ships the public API described in this sprint's spec.

Until then, `import teaf` raises `ModuleNotFoundError` and this module
cannot be imported or run. `mypy --strict` will report exactly one
error here (unresolved `teaf` import) — that is the expected, documented
signature of the limitation, not a defect.

Intended run command once unblocked:
    uvicorn backend.app:app --reload
"""

from __future__ import annotations

from teaf import Application

from backend.config import get_settings

settings = get_settings()

app = Application(
    name=settings.app_name,
    version=settings.app_version,
    description="Official reference application for the Torus Enterprise Application Framework.",
)
