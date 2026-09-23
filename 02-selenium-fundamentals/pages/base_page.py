"""
BasePage: shared WebDriverWait-based actions for every page object.

Every concrete page object (LoginPage, InventoryPage, ...) inherits from
this class instead of calling `driver.find_element(...)` directly. That's
the core value of the Page Object Model: waiting/finding logic lives in
exactly one place, so if it ever needs to change (e.g. swap in a different
wait strategy, add retry logic, add logging) it changes once, not in every
page object and every test.
"""

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DEFAULT_TIMEOUT_SECONDS = 10


class BasePage:
    """Common actions available to every page object in this suite."""

    def __init__(self, driver: WebDriver, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.driver = driver
        # Each page object gets its own WebDriverWait instance rather than a
        # shared one, so an individual page could be given a longer/shorter
        # timeout if a particular page is known to be slower (e.g. a page
        # with a heavy initial data load).
        self.wait = WebDriverWait(driver, timeout)

    def wait_visible(self, locator: tuple) -> WebElement:
        """
        Waits until the element is present in the DOM *and* visible.

        Visibility (not just presence) is the right condition before most
        interactions — an element can exist in the DOM while hidden behind
        a loading spinner or an off-screen animation, and interacting with
        it too early is a classic source of flaky tests.
        """
        return self.wait.until(EC.visibility_of_element_located(locator))

    def wait_clickable(self, locator: tuple) -> WebElement:
        """
        Waits until the element is visible AND enabled — the right
        condition immediately before a `.click()`. Using this instead of
        `wait_visible` for clicks avoids "element not interactable" errors
        on elements that are visible but still disabled (e.g. a submit
        button before form validation completes).
        """
        return self.wait.until(EC.element_to_be_clickable(locator))

    def click(self, locator: tuple) -> None:
        """Waits for clickability, then clicks — never clicks blind."""
        self.wait_clickable(locator).click()

    def type_text(self, locator: tuple, text: str, clear_first: bool = True) -> None:
        """
        Waits for visibility, optionally clears, then types.

        Clearing first is the default because Selenium's `send_keys`
        *appends* to existing content — skipping `clear()` is a common
        source of tests that "randomly" submit "old_valuenew_value".
        """
        element = self.wait_visible(locator)
        if clear_first:
            element.clear()
        element.send_keys(text)

    def get_text(self, locator: tuple) -> str:
        """Waits for visibility, then reads the element's rendered text."""
        return self.wait_visible(locator).text

    def is_visible(self, locator: tuple, timeout: int = 3) -> bool:
        """
        Non-raising visibility check, for optional/conditional elements
        (e.g. "is there an error banner or not?"). Uses a short local
        timeout rather than self.wait's default so a legitimately-absent
        element doesn't slow every caller down to the full page timeout.
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except Exception:
            return False

    def open_url(self, url: str) -> None:
        """Thin wrapper kept for symmetry/readability in page objects
        (`self.open_url(URL)` reads more clearly than a bare `driver.get`
        scattered across page object methods)."""
        self.driver.get(url)
