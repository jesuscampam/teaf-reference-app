"""Tests for app.modules.task.routes — plain FastAPI, isolated from TEAF's
`Application`.

The router is mounted on a bare `FastAPI()` here rather than on the real
`Application`, so a failure points at the HTTP layer and nothing else.
Full-stack behaviour is covered in test_integration.py.

Since Sprint A3 every handler carries `@authorize(permission=...)`, so the
isolated app needs the same `SecurityMiddleware` the real one installs —
otherwise these tests would exercise a decorator that never sees a
security context, which is not the code that runs in production. The
wiring is TEAF's, only the token is minted here.

`client` is authenticated as a read/write account. `anonymous_client` and
`viewer_client` cover the 401 and 403 paths.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from uuid import uuid4

import pytest
from anyio.from_thread import start_blocking_portal
from fastapi import FastAPI
from fastapi.testclient import TestClient
from teaf import (
    Claims,
    Identity,
    IdentityProviderRegistry,
    JWTIdentityProvider,
    JWTProvider,
    Permission,
    PrincipalResolver,
    Role,
    SecurityMiddleware,
    StaticRoleResolver,
)

from app.modules.task.repository import InMemoryTaskRepository
from app.modules.task.routes import create_task_router
from app.modules.task.services import TaskService

_ROLES = {
    "writer": Role(
        name="writer",
        permissions=frozenset({Permission("task.read"), Permission("task.write")}),
    ),
    "reader": Role(name="reader", permissions=frozenset({Permission("task.read")})),
}


@pytest.fixture
def token_provider() -> JWTProvider:
    return JWTProvider(secret=secrets.token_urlsafe(32))


@pytest.fixture
def anonymous_client(token_provider: JWTProvider) -> Iterator[TestClient]:
    """No credentials — every endpoint should answer 401."""
    service = TaskService(InMemoryTaskRepository())
    app = FastAPI()
    app.include_router(create_task_router(lambda: service))
    app.add_middleware(
        SecurityMiddleware,
        provider_registry=IdentityProviderRegistry(
            [JWTIdentityProvider(token_provider=token_provider)]
        ),
        principal_resolver=PrincipalResolver(
            role_resolver=StaticRoleResolver(roles_by_name=_ROLES)
        ),
    )
    with TestClient(app) as test_client:
        yield test_client


def _token_for(provider: JWTProvider, role: str) -> str:
    """Mint a token from a synchronous fixture.

    `JWTProvider.issue` is async, and `asyncio.run` cannot be used here:
    the session-scoped `client` fixture in tests/conftest.py keeps a loop
    alive, and starting a second one in the same thread raises "Cannot run
    the event loop while another loop is running". A blocking portal runs
    the coroutine on its own loop in its own thread, so it works whatever
    else is running.
    """
    identity = Identity(
        id=f"{role}-account",
        provider_id="test",
        claims=Claims(sub=f"{role}-account", roles=frozenset({role})),
    )
    with start_blocking_portal() as portal:
        return portal.call(provider.issue, identity).access_token


@pytest.fixture
def client(anonymous_client: TestClient, token_provider: JWTProvider) -> TestClient:
    """Authenticated with both task permissions."""
    anonymous_client.headers["Authorization"] = f"Bearer {_token_for(token_provider, 'writer')}"
    return anonymous_client


@pytest.fixture
def viewer_client(anonymous_client: TestClient, token_provider: JWTProvider) -> TestClient:
    """Authenticated, but read-only — mutating endpoints should answer 403."""
    anonymous_client.headers["Authorization"] = f"Bearer {_token_for(token_provider, 'reader')}"
    return anonymous_client


def _create(client: TestClient, title: str = "a", description: str = "b") -> dict[str, str]:
    response = client.post("/tasks", json={"title": title, "description": description})
    assert response.status_code == 201
    created: dict[str, str] = response.json()
    return created


# -- Reads ---------------------------------------------------------------------


def test_create_and_list(client: TestClient) -> None:
    created = _create(client)

    listed = client.get("/tasks")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created["id"]


def test_list_is_empty_initially(client: TestClient) -> None:
    assert client.get("/tasks").json() == []


def test_new_task_starts_in_todo(client: TestClient) -> None:
    assert _create(client)["status"] == "TODO"


def test_get_missing_returns_404(client: TestClient) -> None:
    response = client.get(f"/tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_get_with_a_malformed_id_returns_422(client: TestClient) -> None:
    assert client.get("/tasks/not-a-uuid").status_code == 422


# -- Writes --------------------------------------------------------------------


def test_update(client: TestClient) -> None:
    created = _create(client)

    response = client.put(f"/tasks/{created['id']}", json={"title": "c", "description": "d"})

    assert response.status_code == 200
    assert response.json()["title"] == "c"


def test_update_missing_returns_404(client: TestClient) -> None:
    response = client.put(f"/tasks/{uuid4()}", json={"title": "c", "description": "d"})

    assert response.status_code == 404


def test_delete(client: TestClient) -> None:
    created = _create(client)

    response = client.delete(f"/tasks/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_missing_returns_404(client: TestClient) -> None:
    assert client.delete(f"/tasks/{uuid4()}").status_code == 404


# -- Status --------------------------------------------------------------------


@pytest.mark.parametrize("target", ["IN_PROGRESS", "DONE"])
def test_patch_status(client: TestClient, target: str) -> None:
    created = _create(client)

    response = client.patch(f"/tasks/{created['id']}/status", json={"status": target})

    assert response.status_code == 200
    assert response.json()["status"] == target


def test_patch_status_missing_returns_404(client: TestClient) -> None:
    response = client.patch(f"/tasks/{uuid4()}/status", json={"status": "DONE"})

    assert response.status_code == 404


def test_patch_status_to_current_status_returns_409(client: TestClient) -> None:
    created = _create(client)

    response = client.patch(f"/tasks/{created['id']}/status", json={"status": "TODO"})

    assert response.status_code == 409
    assert "already" in response.json()["detail"]


def test_patch_status_rejects_an_unknown_status(client: TestClient) -> None:
    created = _create(client)

    response = client.patch(f"/tasks/{created['id']}/status", json={"status": "ARCHIVED"})

    assert response.status_code == 422


def test_complete(client: TestClient) -> None:
    created = _create(client)

    response = client.post(f"/tasks/{created['id']}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "DONE"


def test_complete_missing_returns_404(client: TestClient) -> None:
    assert client.post(f"/tasks/{uuid4()}/complete").status_code == 404


def test_complete_twice_returns_409(client: TestClient) -> None:
    created = _create(client)
    client.post(f"/tasks/{created['id']}/complete")

    assert client.post(f"/tasks/{created['id']}/complete").status_code == 409


# -- Validation ----------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "", "description": "b"},
        {"title": "a", "description": ""},
        {"title": "x" * 201, "description": "b"},
        {"description": "missing title"},
        {"title": "missing description"},
    ],
)
def test_create_rejects_invalid_payloads(client: TestClient, payload: dict[str, str]) -> None:
    assert client.post("/tasks", json=payload).status_code == 422


def test_whitespace_only_title_is_rejected_by_the_service(client: TestClient) -> None:
    """Passes the schema's `min_length` but not the domain rule — 400, not 422."""
    response = client.post("/tasks", json={"title": "   ", "description": "b"})

    assert response.status_code == 400
    assert "blank" in response.json()["detail"]


def test_update_with_a_whitespace_only_title_returns_400(client: TestClient) -> None:
    """Same split as on create: the schema accepts it, the domain rule doesn't."""
    created = _create(client)

    response = client.put(f"/tasks/{created['id']}", json={"title": " ", "description": "ok"})

    assert response.status_code == 400
    assert "blank" in response.json()["detail"]


def test_errors_never_leak_internals(client: TestClient) -> None:
    body = client.get(f"/tasks/{uuid4()}").json()

    assert set(body) == {"detail"}
    assert "Traceback" not in body["detail"]


# -- Stats ---------------------------------------------------------------------


def test_stats_on_an_empty_list(client: TestClient) -> None:
    assert client.get("/tasks/stats").json() == {
        "total": 0,
        "todo": 0,
        "in_progress": 0,
        "done": 0,
    }


def test_stats_count_each_status(client: TestClient) -> None:
    _create(client, title="stays todo")
    started = _create(client, title="started")
    finished = _create(client, title="finished")
    client.patch(f"/tasks/{started['id']}/status", json={"status": "IN_PROGRESS"})
    client.post(f"/tasks/{finished['id']}/complete")

    assert client.get("/tasks/stats").json() == {
        "total": 3,
        "todo": 1,
        "in_progress": 1,
        "done": 1,
    }


def test_stats_path_is_not_parsed_as_a_task_id(client: TestClient) -> None:
    """Route ordering regression guard: `/tasks/stats` must not hit `/tasks/{id}`."""
    assert client.get("/tasks/stats").status_code == 200


# -- Authentication and authorization ------------------------------------------
#
# Only the *decorator's* effect is checked here — that a permitted token
# reaches the handler and a read-only one does not. The HTTP status codes
# are asserted in test_integration.py instead, against the real
# `Application`: TEAF maps its authentication/authorization exceptions to
# 401/403 in middleware that `create_app()` installs, and that mapping is
# not publicly composable onto a bare `FastAPI()`. Asserting status codes
# here would be asserting something this app never runs.


def test_a_permitted_token_reaches_the_handler(client: TestClient) -> None:
    assert client.get("/tasks").status_code == 200


def test_a_read_only_token_reaches_read_handlers(viewer_client: TestClient) -> None:
    assert viewer_client.get("/tasks").status_code == 200
    assert viewer_client.get("/tasks/stats").status_code == 200


#: Write endpoints paired with a *valid* body. The body matters: FastAPI
#: validates the schema before the handler (and therefore before
#: `@authorize`) runs, so an invalid payload would be rejected as 422
#: without authorization ever being consulted — see the security notes in
#: docs/BOOTSTRAP.md, "Sprint A3".
_WRITE_CALLS: list[tuple[str, str, dict[str, str] | None]] = [
    ("post", "/tasks", {"title": "t", "description": "d"}),
    ("put", f"/tasks/{uuid4()}", {"title": "t", "description": "d"}),
    ("patch", f"/tasks/{uuid4()}/status", {"status": "DONE"}),
    ("delete", f"/tasks/{uuid4()}", None),
    ("post", f"/tasks/{uuid4()}/complete", None),
]


@pytest.mark.parametrize(("method", "path", "body"), _WRITE_CALLS)
def test_write_handlers_refuse_a_read_only_token(
    viewer_client: TestClient, method: str, path: str, body: dict[str, str] | None
) -> None:
    """The decorator stops the request before the handler runs, so nothing
    is created, updated, or deleted. Raised rather than returned — see the
    note above."""
    with pytest.raises(Exception, match="permis|Permis|autoriz|author"):
        viewer_client.request(method, path, json=body)


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [("get", "/tasks", None), ("get", "/tasks/stats", None), *_WRITE_CALLS],
)
def test_handlers_refuse_an_anonymous_request(
    anonymous_client: TestClient, method: str, path: str, body: dict[str, str] | None
) -> None:
    with pytest.raises(Exception, match="autenticación|authentication"):
        anonymous_client.request(method, path, json=body)
