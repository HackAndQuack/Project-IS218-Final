"""
Browser-driven Playwright E2E tests for the Calculations BREAD flows.

Unlike tests/e2e/test_fastapi_calculator.py (which drives the API directly with
`requests`), these tests actually load the rendered pages, fill in forms, click
buttons, and assert on what the browser shows the user - exercising the real
front-end (templates + inline JavaScript) end to end.

Each test registers and logs in as its own fresh user via the UI so tests do not
share calculation data with one another.
"""
import re
from uuid import uuid4

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

fake = Faker()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def unique_user() -> dict:
    """Generate a fresh set of registration fields for one test user."""
    suffix = uuid4().hex[:10]
    return {
        "username": f"e2e_{suffix}",
        "email": f"e2e_{suffix}@example.com",
        "password": "SecurePass123!",
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
    }


def register_and_login_via_ui(page: Page, base_url: str) -> dict:
    """
    Drive the actual /register and /login pages as a real user would:
    fill the forms, submit, and land on /dashboard.

    Returns the user dict used for registration.
    """
    user = unique_user()

    page.goto(f"{base_url}register")
    page.fill("#username", user["username"])
    page.fill("#email", user["email"])
    page.fill("#first_name", user["first_name"])
    page.fill("#last_name", user["last_name"])
    page.fill("#password", user["password"])
    page.fill("#confirm_password", user["password"])
    page.click("#registrationForm button[type=submit]")

    # register.html redirects to /login after a short delay on success
    page.wait_for_url(re.compile(r".*/login$"), timeout=10_000)

    page.fill("#username", user["username"])
    page.fill("#password", user["password"])
    page.click("#loginForm button[type=submit]")

    # login.html redirects to /dashboard after a short delay on success
    page.wait_for_url(re.compile(r".*/dashboard$"), timeout=10_000)
    expect(page.locator("#calculationForm")).to_be_visible()

    return user


def add_calculation_via_ui(page: Page, calc_type: str, inputs_text: str) -> None:
    """Fill and submit the 'New Calculation' form on the dashboard."""
    page.select_option("#calcType", calc_type)
    page.fill("#calcInputs", inputs_text)
    page.click("#calculationForm button[type=submit]")


def first_row_view_link(page: Page):
    return page.locator("#calculationsTable a[href^='/dashboard/view/']").first


# ---------------------------------------------------------------------------
# Positive scenarios: Add, Browse, Read, Edit, Delete
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_add_and_browse_calculation(page: Page, fastapi_server: str):
    register_and_login_via_ui(page, fastapi_server)

    add_calculation_via_ui(page, "addition", "5, 10, 15")

    expect(page.locator("#successAlert")).to_be_visible()
    row = page.locator("#calculationsTable tr").filter(has_text="addition")
    expect(row).to_have_count(1)
    expect(row).to_contain_text("30")


@pytest.mark.e2e
def test_read_calculation_details(page: Page, fastapi_server: str):
    register_and_login_via_ui(page, fastapi_server)
    add_calculation_via_ui(page, "multiplication", "2, 3, 4")
    expect(page.locator("#successAlert")).to_be_visible()

    first_row_view_link(page).click()
    page.wait_for_url(re.compile(r".*/dashboard/view/.+"))

    expect(page.locator("#calculationCard")).to_be_visible()
    details = page.locator("#calcDetails")
    expect(details).to_contain_text("multiplication")
    expect(details).to_contain_text("2, 3, 4")
    expect(page.locator("#calcDetails")).to_contain_text("24")


@pytest.mark.e2e
def test_edit_calculation_updates_result(page: Page, fastapi_server: str):
    register_and_login_via_ui(page, fastapi_server)
    add_calculation_via_ui(page, "addition", "1, 1")
    expect(page.locator("#successAlert")).to_be_visible()

    first_row_view_link(page).click()
    page.wait_for_url(re.compile(r".*/dashboard/view/.+"))
    page.click("#editLink")
    page.wait_for_url(re.compile(r".*/dashboard/edit/.+"))

    expect(page.locator("#editCard")).to_be_visible()
    page.fill("#calcInputs", "40, 2")
    page.click("#editCalculationForm button[type=submit]")

    # edit_calculation.html redirects back to the view page after a successful save
    page.wait_for_url(re.compile(r".*/dashboard/view/.+"), timeout=10_000)
    expect(page.locator("#calcDetails")).to_contain_text("42")


@pytest.mark.e2e
def test_delete_calculation(page: Page, fastapi_server: str):
    register_and_login_via_ui(page, fastapi_server)
    add_calculation_via_ui(page, "subtraction", "10, 3")
    expect(page.locator("#successAlert")).to_be_visible()

    page.on("dialog", lambda dialog: dialog.accept())

    first_row_view_link(page).click()
    page.wait_for_url(re.compile(r".*/dashboard/view/.+"))
    page.click("#deleteBtn")

    page.wait_for_url(re.compile(r".*/dashboard$"), timeout=10_000)
    expect(page.locator("#calculationsTable")).not_to_contain_text("subtraction")


# ---------------------------------------------------------------------------
# Negative scenarios
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_add_calculation_rejects_single_number(page: Page, fastapi_server: str):
    register_and_login_via_ui(page, fastapi_server)

    add_calculation_via_ui(page, "addition", "5")

    expect(page.locator("#errorAlert")).to_be_visible()
    expect(page.locator("#errorMessage")).to_contain_text("at least two")
    # No calculation should have been created.
    expect(page.locator("#calculationsTable")).to_contain_text("No calculations found")


@pytest.mark.e2e
def test_edit_calculation_rejects_division_by_zero(page: Page, fastapi_server: str):
    register_and_login_via_ui(page, fastapi_server)
    add_calculation_via_ui(page, "division", "100, 5")
    expect(page.locator("#successAlert")).to_be_visible()

    first_row_view_link(page).click()
    page.wait_for_url(re.compile(r".*/dashboard/view/.+"))
    page.click("#editLink")
    page.wait_for_url(re.compile(r".*/dashboard/edit/.+"))

    page.fill("#calcInputs", "100, 0")
    page.click("#editCalculationForm button[type=submit]")

    expect(page.locator("#errorAlert")).to_be_visible()
    expect(page.locator("#errorMessage")).to_contain_text("Division by zero")

    # The calculation itself must be unchanged - reload the view page and check.
    page.goto(f"{fastapi_server}dashboard")
    row = page.locator("#calculationsTable tr").filter(has_text="division")
    expect(row).to_contain_text("20")  # 100 / 5, unchanged


@pytest.mark.e2e
@pytest.mark.parametrize("path_suffix", ["dashboard"])
def test_dashboard_requires_login(page: Page, fastapi_server: str, path_suffix: str):
    # A brand-new context/page has no access_token in localStorage.
    page.goto(f"{fastapi_server}{path_suffix}")
    page.wait_for_url(re.compile(r".*/login$"), timeout=10_000)
    expect(page.locator("#loginForm")).to_be_visible()


@pytest.mark.e2e
def test_view_and_edit_pages_require_login(page: Page, fastapi_server: str):
    fake_id = str(uuid4())

    page.goto(f"{fastapi_server}dashboard/view/{fake_id}")
    page.wait_for_url(re.compile(r".*/login$"), timeout=10_000)

    page.goto(f"{fastapi_server}dashboard/edit/{fake_id}")
    page.wait_for_url(re.compile(r".*/login$"), timeout=10_000)


@pytest.mark.e2e
def test_login_rejects_invalid_credentials(page: Page, fastapi_server: str):
    page.goto(f"{fastapi_server}login")
    page.fill("#username", f"nonexistent_{uuid4().hex[:8]}")
    page.fill("#password", "WrongPassword123!")
    page.click("#loginForm button[type=submit]")

    expect(page.locator("#errorAlert")).to_be_visible()
    # Should remain on the login page, not redirect to the dashboard.
    expect(page).to_have_url(re.compile(r".*/login$"))
