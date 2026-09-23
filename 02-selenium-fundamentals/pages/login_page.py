"""
LoginPage: page object for https://www.saucedemo.com/ (the login screen).

Tests interact with this class, never with raw locators/`driver` calls —
that's what keeps test_login.py readable as plain business logic ("log in,
assert redirected") instead of a maze of `find_element` calls.
"""

from selenium.webdriver.common.by import By

from pages.base_page import BasePage

BASE_URL = "https://www.saucedemo.com/"


class LoginPage(BasePage):
    # Locators grouped at the top of the class (not inline in methods) so
    # that when saucedemo's DOM changes, there's exactly one place to fix it.
    # CSS selectors are preferred here over XPath: they're faster for the
    # browser to evaluate and easier for the next engineer to read.
    USERNAME_INPUT = (By.CSS_SELECTOR, "#user-name")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "#password")
    LOGIN_BUTTON = (By.CSS_SELECTOR, "#login-button")
    ERROR_MESSAGE = (By.CSS_SELECTOR, '[data-test="error"]')

    def open(self) -> None:
        """Navigates directly to the login page (it's saucedemo's homepage)."""
        self.open_url(BASE_URL)
        # Fail fast with a clear wait-timeout error here rather than letting
        # a not-yet-loaded page produce a confusing failure two lines later
        # inside login().
        self.wait_visible(self.USERNAME_INPUT)

    def login(self, username: str, password: str) -> None:
        """Fills the login form and submits it."""
        self.type_text(self.USERNAME_INPUT, username)
        self.type_text(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)

    def get_error_message(self) -> str:
        """
        Returns the text of the login error banner.

        Callers (tests) are expected to only call this after triggering a
        failed login — if no error is showing, wait_visible will raise a
        TimeoutException, which is the correct failure mode: it means the
        expected error never appeared.
        """
        return self.get_text(self.ERROR_MESSAGE)
