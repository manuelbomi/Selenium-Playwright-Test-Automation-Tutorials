"""
Payoff of the storage_state technique: this test never touches the login
form. It goes straight to /inventory.html using a browser context that
already has an authenticated session baked in (see conftest.py's
`authenticated_page` fixture, backed by auth_setup/generate_auth_state.py).

Compare this to a typical Selenium suite, where every test class re-runs the
full login flow in setUp() -- multiplying both login time and login flakiness
across the whole suite. Here, login happens ONCE (ahead of the test run, or
once per CI job) and every test that needs to be logged in amortizes that
cost to effectively zero.
"""

import re

from playwright.sync_api import Page, expect


def test_add_item_to_cart_without_logging_in(authenticated_page: Page):
    # Straight to the inventory page -- no username/password, no login click.
    authenticated_page.goto("/inventory.html")

    # Proof the saved session was honored: no redirect back to the login page,
    # and the inventory UI is what's actually on screen.
    expect(authenticated_page).to_have_url(re.compile(r".*inventory\.html"))
    expect(authenticated_page.get_by_text("Products")).to_be_visible()

    authenticated_page.locator("#add-to-cart-sauce-labs-backpack").click()

    cart_badge = authenticated_page.locator(".shopping_cart_badge")
    expect(cart_badge).to_have_text("1")
