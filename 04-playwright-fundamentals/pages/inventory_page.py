"""
inventory_page.py

Page object for saucedemo's /inventory.html products page.

Design note: rather than hardcoding one locator per SKU, `add_item_to_cart`
builds the button locator from the product's display name using
saucedemo's own naming convention for its add-to-cart buttons
(`data-test="add-to-cart-<slugified-product-name>"`, e.g. "Sauce Labs
Backpack" -> `add-to-cart-sauce-labs-backpack`). That keeps this page
object usable for the whole catalog without a giant hardcoded locator map
-- a pattern worth knowing once a real catalog grows past a handful of
items.
"""

import re

from playwright.sync_api import Page

from pages.base_page import BasePage


class InventoryPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.inventory_items = page.locator(".inventory_item")
        self.cart_badge = page.locator(".shopping_cart_badge")

    @staticmethod
    def _slugify(item_name: str) -> str:
        """
        'Sauce Labs Backpack' -> 'sauce-labs-backpack', matching the
        data-test attributes saucedemo generates for its standard catalog.
        Covers every item in the default product set; a name with unusual
        punctuation would need extra handling, which is a reasonable
        exercise for extending this page object.
        """
        return re.sub(r"\s+", "-", item_name.strip().lower())

    def add_item_to_cart(self, item_name: str) -> None:
        """
        Click the "Add to cart" button for the given product.

        We use a data-test attribute selector rather than get_by_role or
        get_by_text here because every product tile has a visually and
        semantically identical "Add to cart" button -- role/text alone
        can't tell them apart. This is the README's "CSS/attribute
        locator" fallback case in practice.
        """
        slug = self._slugify(item_name)
        self.page.locator(f'[data-test="add-to-cart-{slug}"]').click()

    def get_cart_count(self) -> int:
        """
        Return the number on the cart badge, or 0 if the badge isn't
        rendered at all -- saucedemo removes the badge element entirely
        when the cart is empty rather than showing "0".

        `Locator.count()` does NOT auto-wait (it just checks the DOM right
        now), which is exactly what we want here: we're asking "does a
        badge currently exist?", not "wait for a badge to appear."
        """
        if self.cart_badge.count() == 0:
            return 0
        return int(self.cart_badge.text_content())
