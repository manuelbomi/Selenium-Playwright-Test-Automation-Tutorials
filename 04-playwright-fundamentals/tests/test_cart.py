"""
test_cart.py

Logs in as standard_user, adds products to the cart, and asserts on the
cart badge count -- using web-first `expect()` assertions throughout
instead of reading the badge's text once and comparing it with a bare
`assert`.
"""

import pytest
from playwright.sync_api import Page, expect

from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage


@pytest.fixture
def inventory_page(page: Page) -> InventoryPage:
    """Log in as standard_user and hand back an InventoryPage that's
    already on /inventory.html."""
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login("standard_user", "secret_sauce")
    return InventoryPage(page)


def test_add_single_item_updates_cart_badge(inventory_page: InventoryPage) -> None:
    inventory_page.add_item_to_cart("Sauce Labs Backpack")

    # to_have_text() polls the badge until it reads "1" or the default
    # timeout elapses, closing the tiny window between the click and the
    # React-driven badge re-render -- a bare `assert badge.text_content()
    # == "1"` could read the DOM a moment too early and fail flakily.
    expect(inventory_page.cart_badge).to_have_text("1")


def test_add_multiple_items_updates_cart_badge(inventory_page: InventoryPage) -> None:
    inventory_page.add_item_to_cart("Sauce Labs Backpack")
    inventory_page.add_item_to_cart("Sauce Labs Bike Light")
    inventory_page.add_item_to_cart("Sauce Labs Bolt T-Shirt")

    expect(inventory_page.cart_badge).to_have_text("3")
    # A plain assert is fine here too, immediately after an expect() has
    # already confirmed the badge settled on its final value above.
    assert inventory_page.get_cart_count() == 3


def test_cart_badge_absent_when_cart_is_empty(inventory_page: InventoryPage) -> None:
    """Before adding anything, saucedemo renders no badge element at all
    (not a "0") -- get_cart_count() should treat that as zero."""
    expect(inventory_page.cart_badge).to_have_count(0)
    assert inventory_page.get_cart_count() == 0
