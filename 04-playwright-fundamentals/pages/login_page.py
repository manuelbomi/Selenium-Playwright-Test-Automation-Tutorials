"""
login_page.py

Page object for https://www.saucedemo.com/ -- the login screen.

Locator strategy (see README "Locators" for the full priority order and
why): saucedemo's login form is plain HTML with no accessible roles/labels
that uniquely identify the username/password fields or the submit button,
so role/label-based locators (get_by_role, get_by_label) don't apply
cleanly here. We fall back to CSS id selectors, which is exactly the
"no good semantics available" case the README calls out for choosing CSS
over accessibility locators.

The error banner is the one element with a stable, purpose-built
attribute (`data-test="error"`). Playwright's `get_by_test_id()` is built
for this pattern, but it looks for `data-testid` by default -- saucedemo
uses `data-test` (no "id" suffix), so we address it with a CSS attribute
selector instead of reconfiguring Playwright's global test-id attribute
for one element.
"""

from playwright.sync_api import Page

from pages.base_page import BasePage


class LoginPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.username_input = page.locator("#user-name")
        self.password_input = page.locator("#password")
        self.login_button = page.locator("#login-button")
        self.error_message = page.locator('[data-test="error"]')

    def goto(self) -> None:
        """Navigate to the login page (the app's root)."""
        self.navigate("/")

    def login(self, username: str, password: str) -> None:
        """
        Fill in credentials and submit the login form.

        No explicit waits precede these calls. `fill()` and `click()` each
        run Playwright's actionability checks (visible, stable, enabled,
        receives events) immediately before acting, so by the time
        `login_button.click()` executes, Playwright has already confirmed
        the button is really clickable -- there's nothing extra to wait
        for. Compare with Selenium (Tutorial 2), where the same flow
        needed `WebDriverWait(driver).until(EC.element_to_be_clickable(...))`
        ahead of every interaction.
        """
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def get_error_message(self) -> str:
        """
        Return the error banner's text.

        `text_content()` on a Locator auto-waits for the element to be
        attached before reading it, so this is safe to call immediately
        after `login()` even though the error banner only appears after
        the (client-side) form submission completes.
        """
        return self.error_message.text_content()
