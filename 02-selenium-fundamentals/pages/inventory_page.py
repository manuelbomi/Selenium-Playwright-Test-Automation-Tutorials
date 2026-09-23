"""
InventoryPage: page object for the post-login products page on saucedemo.com.
"""

from selenium.webdriver.common.by import By

from pages.base_page import BasePage

INVENTORY_URL_PATH = "inventory.html"


class InventoryPage(BasePage):
    INVENTORY_ITEM = (By.CSS_SELECTOR, ".inventory_item")
    CART_BADGE = (By.CSS_SELECTOR, ".shopping_cart_badge")

    # Every "Add to cart" button has a predictable `data-test` id
    # (e.g. "add-to-cart-sauce-labs-backpack") built from the product name.
    # That works great for a *known, fixed* product name, so we keep it as
    # the direct/preferred path.
    ADD_TO_CART_BY_DATA_TEST = "button[data-test='add-to-cart-{slug}']"

    # Fallback: look up a product's "Add to cart" button *by its visible
    # name text* instead of a derived data-test slug. This is a good example
    # of when XPath earns its keep over CSS: CSS selectors have no way to
    # match on text content, and no way to walk from a matched node *up* to
    # an ancestor. Here we find the product name text, then climb to the
    # enclosing .inventory_item card, then look back down for its button.
    ITEM_NAME_TEXT_XPATH = "//div[@class='inventory_item_name' and text()='{name}']"
    ANCESTOR_CARD_BUTTON_XPATH = "./ancestor::div[@class='inventory_item']//button"

    def _slugify(self, item_name: str) -> str:
        """Mirrors saucedemo's convention of turning 'Sauce Labs Backpack'
        into the 'sauce-labs-backpack' slug used in its data-test ids."""
        return item_name.lower().replace(" ", "-")

    def add_item_to_cart(self, item_name: str) -> None:
        """
        Adds a product to the cart by its visible display name, e.g.
        "Sauce Labs Backpack". Tries the fast, direct data-test locator
        first; falls back to the text+traversal XPath for product names
        that don't map cleanly to the slug convention (e.g. names with
        punctuation like "Test.allTheThings() T-Shirt (Red)").
        """
        slug = self._slugify(item_name)
        direct_locator = (
            By.CSS_SELECTOR,
            self.ADD_TO_CART_BY_DATA_TEST.format(slug=slug),
        )

        if self.is_visible(direct_locator, timeout=2):
            self.click(direct_locator)
            return

        name_element = self.wait_visible(
            (By.XPATH, self.ITEM_NAME_TEXT_XPATH.format(name=item_name))
        )
        button = name_element.find_element(
            By.XPATH, self.ANCESTOR_CARD_BUTTON_XPATH
        )
        button.click()

    def get_cart_count(self) -> int:
        """
        Returns the number shown on the cart badge, or 0 if the badge isn't
        present (an empty cart renders with no badge element at all, rather
        than a badge showing "0").
        """
        if not self.is_visible(self.CART_BADGE, timeout=2):
            return 0
        return int(self.get_text(self.CART_BADGE))

    def get_inventory_item_count(self) -> int:
        """Number of product cards currently rendered on the page — a handy
        sanity check that the page actually loaded before interacting with it."""
        return len(self.driver.find_elements(*self.INVENTORY_ITEM))
