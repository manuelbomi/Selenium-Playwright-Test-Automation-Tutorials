"""
test_login.py

Login scenarios, deliberately mirroring Tutorial 2's Selenium login suite
(successful login, a locked-out user, and a wrong password) so the two
frameworks can be compared test-for-test.

Notice what's absent: there's no driver setup/teardown code anywhere in
this file. pytest-playwright's `page` fixture already gives every test a
fresh, isolated browser context and page, and tears it down automatically
-- see conftest.py and README "Built-in Fixtures".
"""

import pytest
from playwright.sync_api import Page, expect

from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    """A LoginPage wired to this test's isolated `page`, already
    navigated to the login screen."""
    lp = LoginPage(page)
    lp.goto()
    return lp


def test_successful_login(login_page: LoginPage, page: Page) -> None:
    """A valid standard_user should land on the inventory page."""
    login_page.login("standard_user", "secret_sauce")

    # expect() is a web-first assertion: it polls/retries against the live
    # page until the condition holds or the timeout elapses, rather than
    # reading the URL/DOM exactly once like a bare `assert`. That absorbs
    # the brief gap between clicking "Login" and the app navigating, with
    # no manual wait_for_* call needed.
    expect(page).to_have_url("https://www.saucedemo.com/inventory.html")

    inventory_page = InventoryPage(page)
    expect(inventory_page.inventory_items.first).to_be_visible()


def test_locked_out_user_shows_error(login_page: LoginPage) -> None:
    """locked_out_user is intentionally blocked by saucedemo; assert the
    exact error text (mirrors Tutorial 2's failure-path coverage)."""
    login_page.login("locked_out_user", "secret_sauce")

    expect(login_page.error_message).to_be_visible()
    assert login_page.get_error_message() == (
        "Epic sadface: Sorry, this user has been locked out."
    )


def test_wrong_password_shows_error(login_page: LoginPage) -> None:
    """A valid username with an incorrect password gets saucedemo's
    generic credentials-mismatch error."""
    login_page.login("standard_user", "not_the_real_password")

    expect(login_page.error_message).to_be_visible()
    assert login_page.get_error_message() == (
        "Epic sadface: Username and password do not match any user "
        "in this service"
    )
