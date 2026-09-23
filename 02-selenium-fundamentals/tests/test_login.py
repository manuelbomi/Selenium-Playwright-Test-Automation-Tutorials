"""
Tests for the saucedemo.com login flow.

Notice these tests read like plain English business rules ("valid login
redirects to inventory", "locked-out user sees an error") with none of the
locator/wait plumbing visible — that's the POM pattern paying off.
"""

import pytest

from pages.login_page import LoginPage

VALID_USERNAME = "standard_user"
LOCKED_OUT_USERNAME = "locked_out_user"
VALID_PASSWORD = "secret_sauce"


@pytest.mark.smoke
def test_successful_login_redirects_to_inventory_page(driver):
    login_page = LoginPage(driver)
    login_page.open()

    login_page.login(VALID_USERNAME, VALID_PASSWORD)

    # A URL assertion is a simple, reliable way to confirm navigation
    # happened — no need to wait on a specific element here since the
    # BasePage's waits inside login() already ensured the click completed.
    assert "/inventory.html" in driver.current_url


@pytest.mark.smoke
def test_locked_out_user_sees_locked_out_error(driver):
    login_page = LoginPage(driver)
    login_page.open()

    login_page.login(LOCKED_OUT_USERNAME, VALID_PASSWORD)

    # Asserting on the exact copy (not just "an error appeared") catches
    # regressions where the *wrong* error is shown for the *right* reason —
    # a class of bug that a looser assertion would silently let through.
    assert login_page.get_error_message() == (
        "Epic sadface: Sorry, this user has been locked out."
    )


def test_wrong_password_shows_generic_error(driver):
    login_page = LoginPage(driver)
    login_page.open()

    login_page.login(VALID_USERNAME, "not_the_real_password")

    assert login_page.get_error_message() == (
        "Epic sadface: Username and password do not match any user "
        "in this service"
    )
    # Plain `assert` is all pytest needs — its assertion rewriting shows a
    # full diff of both sides on failure, so there's no need for
    # unittest-style self.assertEqual(...) helper methods.
    assert "/inventory.html" not in driver.current_url
