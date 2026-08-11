"""The boundary this whole repository exists to prove.

Two claims, both enforced here rather than left to a README:

1. The application starts through TEAF's **public** API — `from teaf
   import Application` and nothing else.
2. No source file reaches into `teaf._internal` (or the pre-Sprint-2.6.2
   `backend.*` namespace it used to live in).

Claim 2 is checked by parsing every file with `ast` instead of grepping,
so a match inside a string, comment, or docstring can't produce a false
failure — and an import can't hide from it by being written oddly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOTS = (_REPO_ROOT / "app", _REPO_ROOT / "tests")

#: Namespaces this application must never import. `teaf._internal` is
#: TEAF's private implementation; `backend` is where that code lived
#: before TEAF v0.6.2-alpha and is equally off-limits.
_FORBIDDEN_ROOTS = ("teaf._internal", "backend")


def _python_files() -> list[Path]:
    return sorted(path for root in _SOURCE_ROOTS for path in root.rglob("*.py"))


def _imported_modules(path: Path) -> list[tuple[int, str]]:
    """Every module name imported by `path`, with the line it appears on."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.append((node.lineno, node.module))
    return found


def _is_forbidden(module: str) -> bool:
    return any(module == root or module.startswith(f"{root}.") for root in _FORBIDDEN_ROOTS)


def test_application_is_importable_from_the_public_package() -> None:
    from teaf import Application

    assert isinstance(Application, type)


def test_the_running_app_is_a_teaf_application() -> None:
    from teaf import Application

    from app.main import app

    assert isinstance(app, Application)


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: str(p.relative_to(_REPO_ROOT)))
def test_no_source_file_imports_a_private_teaf_namespace(path: Path) -> None:
    offenders = [
        f"line {lineno}: {module}"
        for lineno, module in _imported_modules(path)
        if _is_forbidden(module)
    ]

    assert not offenders, f"{path.relative_to(_REPO_ROOT)} imports a private namespace: {offenders}"


def test_the_audit_actually_scans_the_application() -> None:
    """Guard against the check passing because it found nothing to check."""
    scanned = _python_files()

    assert len(scanned) > 10
    assert _REPO_ROOT / "app" / "main.py" in scanned


def test_the_audit_would_catch_a_violation(tmp_path: Path) -> None:
    """Prove the detector detects — otherwise the suite above is theatre."""
    offender = tmp_path / "offender.py"
    offender.write_text("from teaf._internal.runtime.runtime import Runtime\n", encoding="utf-8")

    modules = [module for _, module in _imported_modules(offender)]

    assert any(_is_forbidden(module) for module in modules)
