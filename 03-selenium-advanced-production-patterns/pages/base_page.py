"""
pages/base_page.py — shared behavior for every page object in this suite.

This extends the BasePage concept introduced in Tutorial 2
(../02-selenium-fundamentals/pages/base_page.py) with the widget-handling
primitives every real-world application eventually needs: iframes, native
browser dialogs (alerts/confirms/prompts), multiple windows/tabs, and file
upload inputs.

DESIGN NOTE — avoiding a "God object":
    This class holds only GENERIC Selenium mechanics: waiting, switching
    browsing contexts, clicking, typing. It knows nothing about saucedemo
    or the-internet.herokuapp.com specifically. Page-specific locators and
    page-specific business logic ("log in with these credentials", "add
    this item to the cart") belong in subclasses or in smaller component
    objects that are composed together — never bolted onto BasePage. If
    you find yourself adding an app-specific method here, it belongs one
    layer up. See README.md § "Scaling the Page Object Model" for the full
    composition pattern (e.g. a HeaderComponent + CartComponent used by
    multiple page objects instead of one 500-line InventoryPage).
"""
from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import config


class BasePage:
    """Common waits + widget-handling helpers reused by every page object."""

    def __init__(self, driver: WebDriver, timeout: int | None = None):
        self.driver = driver
        self.timeout = timeout or config.explicit_wait
        self.wait = WebDriverWait(self.driver, self.timeout)

    # -- core waits -----------------------------------------------------------
    # Always prefer these over time.sleep(). A hardcoded sleep either wastes
    # time (waiting longer than necessary on a fast run) or isn't long enough
    # (flaky failures on a slow one) — see the README's Best Practices
    # Checklist: "no hardcoded waits."

    def find(self, locator) -> WebElement:
        return self.wait.until(EC.presence_of_element_located(locator))

    def find_clickable(self, locator) -> WebElement:
        return self.wait.until(EC.element_to_be_clickable(locator))

    def find_all(self, locator):
        return self.wait.until(EC.presence_of_all_elements_located(locator))

    def click(self, locator):
        self.find_clickable(locator).click()

    def type_text(self, locator, text: str):
        element = self.find(locator)
        element.clear()
        element.send_keys(text)

    def get_text(self, locator) -> str:
        return self.find(locator).text

    # -- iframes ----------------------------------------------------------------

    def switch_to_iframe(self, locator):
        """
        Switch the driver's focus into an iframe.

        Until this is called, Selenium cannot see elements that live inside
        the iframe's document — locating them raises NoSuchElementException
        even though they're visibly on the page, because the driver is
        still looking at the parent document's DOM, not the iframe's.
        """
        return self.wait.until(EC.frame_to_be_available_and_switch_to_it(locator))

    def switch_to_default_content(self):
        """Return focus to the top-level page after finishing work inside an iframe."""
        self.driver.switch_to.default_content()

    # -- JS alerts / confirms / prompts ------------------------------------------

    def wait_for_alert(self):
        self.wait.until(EC.alert_is_present())
        return self.driver.switch_to.alert

    def accept_alert(self) -> str:
        """Click OK on a JS alert/confirm; returns its text before it closes."""
        alert = self.wait_for_alert()
        text = alert.text
        alert.accept()
        return text

    def dismiss_alert(self) -> str:
        """Click Cancel on a JS confirm/prompt; returns its text before it closes."""
        alert = self.wait_for_alert()
        text = alert.text
        alert.dismiss()
        return text

    def accept_prompt(self, input_text: str) -> str:
        """Type into a JS prompt() dialog, then accept it."""
        alert = self.wait_for_alert()
        text = alert.text
        alert.send_keys(input_text)
        alert.accept()
        return text

    # -- multiple windows / tabs --------------------------------------------------

    def switch_to_new_window(self, previous_handles):
        """
        Wait for a new window/tab to open, then switch to it.

        `previous_handles` must be captured (via `driver.window_handles`)
        IMMEDIATELY BEFORE the action that opens the new window — otherwise
        there's no reliable way to tell which handle is the new one.
        """
        self.wait.until(lambda d: len(d.window_handles) > len(previous_handles))
        new_handle = (set(self.driver.window_handles) - set(previous_handles)).pop()
        self.driver.switch_to.window(new_handle)
        return new_handle

    def switch_to_window_by_title(self, title: str, timeout: int | None = None):
        """Iterate open window handles and switch to the first one matching `title`."""
        wait = WebDriverWait(self.driver, timeout or self.timeout)

        def _switched_to_matching_title(d):
            for handle in d.window_handles:
                d.switch_to.window(handle)
                if d.title == title:
                    return True
            return False

        wait.until(_switched_to_matching_title)

    def close_and_switch_back(self, original_handle: str):
        """Close the current (extra) window/tab and return focus to `original_handle`."""
        self.driver.close()
        self.driver.switch_to.window(original_handle)

    # -- file upload ----------------------------------------------------------------

    def upload_file(self, file_input_locator, absolute_file_path: str):
        """
        Populate a native <input type="file"> directly via send_keys(path).

        This never opens an OS file-picker dialog — Selenium cannot drive
        native OS dialogs — because browsers accept a path string typed
        straight into the file input element. That also means it works
        headlessly and on Grid nodes with no display.

        `absolute_file_path` must exist on the machine actually running the
        BROWSER, not necessarily the machine running the test process. For
        a local driver these are the same machine. For a Dockerized
        Selenium Grid node they are NOT the same machine unless the file is
        mounted into the node container — see README.md
        "File upload against Grid" for the volume-mount pattern.
        """
        upload_input = self.find(file_input_locator)
        upload_input.send_keys(absolute_file_path)
