"""
Tests for adding items to the cart on saucedemo.com.

Each test logs in fresh via LoginPage rather than sharing a "logged-in
driver" fixture across tests — a little more repetition, but it keeps every
test independent and readable end-to-end without jumping to a fixture
definition to understand the starting state.
"""

import pytest

from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage

VALID_USERNAME = "standard_user"
VALID_PASSWORD = "secret_sauce"


def _login(driver) -> InventoryPage:
    """Shared setup step, not a fixture — see module docstring for why."""
    login_page = LoginPage(driver)
    login_page.open()
    login_page.login(VALID_USERNAME, VALID_PASSWORD)
    return InventoryPage(driver)


@pytest.mark.smoke
def test_adding_one_item_updates_cart_badge_to_one(driver):
    inventory_page = _login(driver)

    inventory_page.add_item_to_cart("Sauce Labs Backpack")

    assert inventory_page.get_cart_count() == 1


def test_adding_two_items_updates_cart_badge_to_two(driver):
    inventory_page = _login(driver)

    inventory_page.add_item_to_cart("Sauce Labs Backpack")
    inventory_page.add_item_to_cart("Sauce Labs Bike Light")

    assert inventory_page.get_cart_count() == 2


def test_cart_badge_is_absent_before_adding_anything(driver):
    inventory_page = _login(driver)

    # Confirms our "no badge element == empty cart" assumption in
    # InventoryPage.get_cart_count() actually holds against the real app,
    # rather than just trusting it silently.
    assert inventory_page.get_cart_count() == 0
