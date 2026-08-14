"""End-to-end: the whole task lifecycle, through the browser, signed in.

This is the demonstration the Reference App exists for — every step is a
click or a keystroke, and every assertion reads the rendered page.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import DEMO_VIEWER, create_task, sign_in

pytestmark = pytest.mark.e2e

#: The badge's DOM text. The uppercase look on screen comes from
#: `text-transform` in CSS, which `to_have_text` does not apply — it reads
#: `textContent`, so these are the strings app.js actually writes.
TODO = "To do"
IN_PROGRESS = "In progress"
DONE = "Done"


def _stats(page: Page) -> dict[str, str]:
    return {
        "total": page.inner_text("#stat-total"),
        "todo": page.inner_text("#stat-todo"),
        "in_progress": page.inner_text("#stat-in-progress"),
        "done": page.inner_text("#stat-done"),
    }


def test_the_full_task_lifecycle(page: Page) -> None:
    """Login, create, edit, advance twice, check the counts, delete."""
    sign_in(page)
    expect(page.locator(".empty-state")).to_be_visible()

    # Create
    create_task(page, "Write the sprint report")
    expect(page.locator(".task-title")).to_have_text("Write the sprint report")
    expect(page.locator(".task-status")).to_have_text(TODO)
    assert _stats(page) == {"total": "1", "todo": "1", "in_progress": "0", "done": "0"}

    # Edit
    page.click(".task-actions button.secondary")
    page.fill(".task-edit-form input:nth-of-type(1)", "Write the final report")
    page.click(".task-edit-form button[type=submit]")
    expect(page.locator(".task-title")).to_have_text("Write the final report")

    # TODO -> IN_PROGRESS
    page.click(".task-actions button:not(.secondary):not(.danger)")
    expect(page.locator(".task-status")).to_have_text(IN_PROGRESS)
    assert _stats(page) == {"total": "1", "todo": "0", "in_progress": "1", "done": "0"}

    # IN_PROGRESS -> DONE
    page.click(".task-actions button:not(.secondary):not(.danger)")
    expect(page.locator(".task-status")).to_have_text(DONE)
    assert _stats(page) == {"total": "1", "todo": "0", "in_progress": "0", "done": "1"}

    # Delete
    page.on("dialog", lambda dialog: dialog.accept())
    page.click(".task-actions button.danger")
    expect(page.locator(".empty-state")).to_be_visible()
    assert _stats(page) == {"total": "0", "todo": "0", "in_progress": "0", "done": "0"}


def test_a_done_task_can_be_reopened(page: Page) -> None:
    sign_in(page)
    create_task(page, "Reopen me")

    page.click(".task-actions button:not(.secondary):not(.danger)")
    expect(page.locator(".task-status")).to_have_text(IN_PROGRESS)
    page.click(".task-actions button:not(.secondary):not(.danger)")
    expect(page.locator(".task-status")).to_have_text(DONE)
    page.click(".task-actions button:not(.secondary):not(.danger)")

    expect(page.locator(".task-status")).to_have_text(TODO)


def test_editing_can_be_cancelled(page: Page) -> None:
    sign_in(page)
    create_task(page, "Leave me alone")

    page.click(".task-actions button.secondary")
    page.fill(".task-edit-form input:nth-of-type(1)", "Changed my mind")
    page.click(".task-edit-form button.secondary")

    expect(page.locator(".task-title")).to_have_text("Leave me alone")


def test_deleting_can_be_cancelled(page: Page) -> None:
    sign_in(page)
    create_task(page, "Do not delete me")

    page.on("dialog", lambda dialog: dialog.dismiss())
    page.click(".task-actions button.danger")

    expect(page.locator(".task-title")).to_have_text("Do not delete me")


def test_tasks_persist_across_a_new_session(page: Page) -> None:
    """Sign out, sign back in, and the data is still there — it lives in
    SQLite on the server, not in the browser."""
    sign_in(page)
    create_task(page, "Outlives the session")

    page.click("#logout-button")
    page.wait_for_url("**/login")
    sign_in(page)

    expect(page.locator(".task-title")).to_have_text("Outlives the session")


def test_the_counters_track_several_tasks(page: Page) -> None:
    sign_in(page)
    create_task(page, "First")
    create_task(page, "Second")
    create_task(page, "Third")

    page.click(".task-item:nth-child(2) .task-actions button:not(.secondary):not(.danger)")
    expect(page.locator(".task-item:nth-child(2) .task-status")).to_have_text(IN_PROGRESS)

    assert _stats(page) == {"total": "3", "todo": "2", "in_progress": "1", "done": "0"}


def test_a_read_only_account_sees_tasks_but_cannot_create(page: Page) -> None:
    """The 403 path, as a user meets it: the create form is not offered."""
    sign_in(page)
    create_task(page, "Visible to everyone")
    page.click("#logout-button")
    page.wait_for_url("**/login")

    sign_in(page, DEMO_VIEWER)

    expect(page.locator(".task-title")).to_have_text("Visible to everyone")
    expect(page.locator("#create-form")).to_be_hidden()
    expect(page.locator("#status-message")).to_contain_text("Read-only")


def test_a_read_only_account_is_refused_by_the_server(page: Page) -> None:
    """Hiding the form is presentation; the refusal is the server's.

    The button is still in the DOM for existing rows, so clicking it
    exercises the real `403` rather than the UI's own guard.
    """
    sign_in(page)
    create_task(page, "Guarded")
    page.click("#logout-button")
    page.wait_for_url("**/login")
    sign_in(page, DEMO_VIEWER)

    page.click(".task-actions button:not(.secondary):not(.danger)")

    expect(page.locator("#status-message")).to_be_visible()
    # Unchanged: the server refused, so the row is exactly as it was.
    expect(page.locator(".task-status")).to_have_text(TODO)
