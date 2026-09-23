"""
base_page.py

BasePage: a thin wrapper around Playwright's `Page` object, shared by every
page object in this suite.

Why it's thin: Selenium's BasePage (Tutorial 2/3) typically grew a pile of
helper methods like `wait_and_click()` or `wait_for_element()`, because
Selenium does not wait for elements to become actionable before you act on
them -- every interaction needed an explicit WebDriverWait wrapped around
it. Playwright's Locator objects perform their own actionability checks
(visible, stable, enabled, receives events) before every action (see
README "Auto-Waiting Explained"), so that entire category of helper method
simply isn't needed here. Keep this class small; resist re-adding
Selenium-style wait helpers "just in case."
"""

from playwright.sync_api import Page


class BasePage:
    """Common functionality shared by all page objects in this suite."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def navigate(self, path: str = "/") -> None:
        """
        Navigate relative to the `base_url` fixture configured in
        conftest.py. Page objects should call this (or `page.goto(path)`
        directly) instead of hardcoding "https://www.saucedemo.com" --
        see conftest.py for the full rationale.
        """
        self.page.goto(path)

    def title(self) -> str:
        """Small convenience wrapper. Only add methods here once a real
        need shows up across multiple page objects -- don't pre-build
        generic helpers speculatively."""
        return self.page.title()
