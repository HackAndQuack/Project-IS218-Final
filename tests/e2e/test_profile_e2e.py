"""
Browser-driven Playwright E2E tests for the profile & password-change flow.

Mirrors the pattern in tests/e2e/test_calculation_bread_e2e.py: each test
registers and logs in as its own fresh user via the UI, then drives the
rendered /profile page directly.
"""
import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.test_calculation_bread_e2e import register_and_login_via_ui


@pytest.mark.e2e
def test_profile_requires_login(page: Page, fastapi_server: str):
    page.goto(f"{fastapi_server}profile")
    page.wait_for_url(re.compile(r".*/login$"), timeout=10_000)
    expect(page.locator("#loginForm")).to_be_visible()


@pytest.mark.e2e
def test_update_profile_persists_after_reload(page: Page, fastapi_server: str):
    register_and_login_via_ui(page, fastapi_server)

    page.goto(f"{fastapi_server}profile")
    expect(page.locator("#profileContent")).to_be_visible()

    page.fill("#first_name", "Updated")
    page.fill("#last_name", "Person")
    page.click("#profileForm button[type=submit]")

    page.wait_for_selector("#toastContainer div")

    page.reload()
    expect(page.locator("#profileContent")).to_be_visible()
    expect(page.locator("#first_name")).to_have_value("Updated")
    expect(page.locator("#last_name")).to_have_value("Person")


@pytest.mark.e2e
def test_change_password_then_relogin(page: Page, fastapi_server: str):
    user = register_and_login_via_ui(page, fastapi_server)

    page.goto(f"{fastapi_server}profile")
    expect(page.locator("#profileContent")).to_be_visible()

    new_password = "NewSecurePass123!"
    page.fill("#current_password", user["password"])
    page.fill("#new_password", new_password)
    page.fill("#confirm_new_password", new_password)
    page.click("#passwordForm button[type=submit]")

    page.wait_for_selector("#toastContainer div")

    # Log out
    page.on("dialog", lambda dialog: dialog.accept())
    page.click("#layoutLogoutBtn")
    page.wait_for_url(re.compile(r".*/login$"), timeout=10_000)

    # Old password should no longer work
    page.fill("#username", user["username"])
    page.fill("#password", user["password"])
    page.click("#loginForm button[type=submit]")
    expect(page.locator("#errorAlert")).to_be_visible()
    expect(page).to_have_url(re.compile(r".*/login$"))

    # New password should work
    page.fill("#username", user["username"])
    page.fill("#password", new_password)
    page.click("#loginForm button[type=submit]")
    page.wait_for_url(re.compile(r".*/dashboard$"), timeout=10_000)


@pytest.mark.e2e
def test_change_password_rejects_wrong_current_password(page: Page, fastapi_server: str):
    user = register_and_login_via_ui(page, fastapi_server)

    page.goto(f"{fastapi_server}profile")
    expect(page.locator("#profileContent")).to_be_visible()

    page.fill("#current_password", "WrongCurrentPass123!")
    page.fill("#new_password", "NewSecurePass123!")
    page.fill("#confirm_new_password", "NewSecurePass123!")
    page.click("#passwordForm button[type=submit]")

    expect(page.locator("#errorAlert")).to_be_visible()
    expect(page.locator("#errorMessage")).to_contain_text("incorrect")


@pytest.mark.e2e
def test_change_password_rejects_mismatched_confirmation(page: Page, fastapi_server: str):
    register_and_login_via_ui(page, fastapi_server)

    page.goto(f"{fastapi_server}profile")
    expect(page.locator("#profileContent")).to_be_visible()

    page.fill("#current_password", "SomePassword123!")
    page.fill("#new_password", "NewSecurePass123!")
    page.fill("#confirm_new_password", "DifferentPass123!")
    page.click("#passwordForm button[type=submit]")

    expect(page.locator("#passwordMatchError")).to_be_visible()
    expect(page.locator("#errorAlert")).to_be_visible()
