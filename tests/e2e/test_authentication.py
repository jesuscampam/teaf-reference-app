"""End-to-end: signing in, signing out, and being kept out.

Driven entirely through the browser — no service is called directly and
no request is forged. What these assert is what a user would see.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import DEMO_USER, WRONG_PASSWORD, sign_in

pytestmark = pytest.mark.e2e

#: The server runs on a random port, so URLs are matched by path.
APP_URL = re.compile(r"^http://127\.0\.0\.1:\d+/$")
LOGIN_URL = re.compile(r"/login$")


def test_login_page_loads(page: Page) -> None:
    page.goto("/login")

    expect(page.locator("#login-form")).to_be_visible()
    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.locator("#login-submit")).to_be_enabled()


def test_invalid_credentials_are_rejected(page: Page) -> None:
    page.goto("/login")
    page.fill("#username", DEMO_USER[0])
    page.fill("#password", WRONG_PASSWORD)
    page.click("#login-submit")

    expect(page.locator("#login-error")).to_be_visible()
    expect(page.locator("#login-error")).to_contain_text("Invalid username or password")
    # Still on the login page, and no session was stored.
    expect(page).to_have_url(LOGIN_URL)
    assert page.evaluate("sessionStorage.getItem('teaf.session')") is None


def test_unknown_user_gets_the_same_message(page: Page) -> None:
    """The UI must not reveal which usernames exist either."""
    page.goto("/login")
    page.fill("#username", "no-such-account")
    page.fill("#password", WRONG_PASSWORD)
    page.click("#login-submit")

    expect(page.locator("#login-error")).to_contain_text("Invalid username or password")


def test_the_form_recovers_after_a_failed_attempt(page: Page) -> None:
    """A rejected attempt must leave a usable form, with the password
    cleared so it is not left sitting on screen."""
    page.goto("/login")
    page.fill("#username", DEMO_USER[0])
    page.fill("#password", WRONG_PASSWORD)
    page.click("#login-submit")
    expect(page.locator("#login-error")).to_be_visible()

    expect(page.locator("#password")).to_have_value("")
    expect(page.locator("#login-submit")).to_be_enabled()

    page.fill("#password", DEMO_USER[1])
    page.click("#login-submit")
    page.wait_for_selector("#task-list")


def test_valid_credentials_reach_the_application(page: Page) -> None:
    sign_in(page)

    expect(page).to_have_url(APP_URL)
    expect(page.locator("#session-username")).to_have_text(DEMO_USER[0])
    expect(page.locator("#task-list")).to_be_visible()


def test_session_survives_a_reload(page: Page) -> None:
    """Session restoration: a reload must not bounce the user to login."""
    sign_in(page)

    page.reload()

    page.wait_for_selector("#task-list")
    expect(page.locator("#session-username")).to_have_text(DEMO_USER[0])


def test_logout_returns_to_the_login_page(page: Page) -> None:
    sign_in(page)

    page.click("#logout-button")

    page.wait_for_url("**/login")
    expect(page.locator("#login-form")).to_be_visible()


def test_logout_clears_the_stored_session(page: Page) -> None:
    sign_in(page)
    assert page.evaluate("sessionStorage.getItem('teaf.session')") is not None

    page.click("#logout-button")
    page.wait_for_url("**/login")

    assert page.evaluate("sessionStorage.getItem('teaf.session')") is None


def test_the_application_is_unreachable_after_logout(page: Page) -> None:
    """The protected-route check: going back to `/` lands on login."""
    sign_in(page)
    page.click("#logout-button")
    page.wait_for_url("**/login")

    page.goto("/")

    page.wait_for_url("**/login")
    expect(page.locator("#login-form")).to_be_visible()


def test_the_application_redirects_a_visitor_who_never_logged_in(page: Page) -> None:
    page.goto("/")

    page.wait_for_url("**/login")
    expect(page.locator("#login-form")).to_be_visible()


def test_an_authenticated_user_is_sent_away_from_the_login_page(page: Page) -> None:
    sign_in(page)

    page.goto("/login")

    page.wait_for_url(APP_URL)
    expect(page.locator("#task-list")).to_be_visible()


def test_a_tampered_token_sends_the_user_back_to_login(page: Page) -> None:
    """A stored session is checked against the server, not trusted."""
    sign_in(page)
    page.evaluate(
        "sessionStorage.setItem('teaf.session',"
        " JSON.stringify({accessToken: 'forged', username: 'demo',"
        " roles: ['user'], permissions: ['task.read','task.write']}))"
    )

    page.goto("/")

    page.wait_for_url("**/login")
    assert page.evaluate("sessionStorage.getItem('teaf.session')") is None
