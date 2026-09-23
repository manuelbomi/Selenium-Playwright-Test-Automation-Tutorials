"""
tests/test_widgets.py — widget-handling patterns against the-internet.herokuapp.com.

saucedemo.com (the target app used elsewhere in this series) has no
iframes, native browser dialogs, popup windows, or file-upload inputs, so
these tests target https://the-internet.herokuapp.com/, a public demo app
built specifically to exercise exactly these mechanics.

Every test here is independent and idempotent: it navigates to its own URL,
depends on no state left behind by another test, and cleans up after
itself (closing extra windows, etc.). That's what makes this file safe to
run with `pytest -n auto` and with `--reruns` — see README.md
"Production Best Practices Checklist".
"""
import os

from selenium.webdriver.common.by import By

from config import config
from pages.base_page import BasePage

WIDGETS_URL = config.widgets_url


class TestIframe:
    def test_can_type_into_rich_text_iframe(self, driver):
        """
        /iframe hosts a TinyMCE rich-text editor whose editable body lives
        inside an <iframe>. We must switch into the iframe before
        interacting with it, then switch back to the default content
        before touching anything on the parent page again.
        """
        page = BasePage(driver)
        driver.get(f"{WIDGETS_URL}/iframe")

        page.switch_to_iframe((By.ID, "mce_0_ifr"))
        editable_body = page.find((By.ID, "tinymce"))
        editable_body.clear()
        editable_body.send_keys("Hello from an automated test!")
        assert "Hello from an automated test!" in editable_body.text, (
            "Text typed into the TinyMCE iframe body was not reflected back"
        )

        # Must switch back out before interacting with anything outside the frame.
        page.switch_to_default_content()
        heading = page.get_text((By.CSS_SELECTOR, "h3"))
        assert heading == "An iFrame containing the TinyMCE WYSIWYG Editor"


class TestJavaScriptDialogs:
    def test_accept_js_alert(self, driver):
        page = BasePage(driver)
        driver.get(f"{WIDGETS_URL}/javascript_alerts")

        page.click((By.CSS_SELECTOR, "button[onclick='jsAlert()']"))
        alert_text = page.accept_alert()

        assert alert_text == "I am a JS Alert"
        result = page.get_text((By.ID, "result"))
        assert result == "You successfully clicked an alert", (
            f"Expected confirmation text after accepting alert, got: {result!r}"
        )

    def test_dismiss_js_confirm(self, driver):
        page = BasePage(driver)
        driver.get(f"{WIDGETS_URL}/javascript_alerts")

        page.click((By.CSS_SELECTOR, "button[onclick='jsConfirm()']"))
        alert_text = page.dismiss_alert()

        assert alert_text == "I am a JS Confirm"
        result = page.get_text((By.ID, "result"))
        assert result == "You clicked: Cancel", (
            f"Dismissing the confirm should register as Cancel, got: {result!r}"
        )

    def test_accept_js_confirm(self, driver):
        page = BasePage(driver)
        driver.get(f"{WIDGETS_URL}/javascript_alerts")

        page.click((By.CSS_SELECTOR, "button[onclick='jsConfirm()']"))
        page.accept_alert()

        result = page.get_text((By.ID, "result"))
        assert result == "You clicked: Ok", (
            f"Accepting the confirm should register as Ok, got: {result!r}"
        )

    def test_js_prompt_with_input(self, driver):
        page = BasePage(driver)
        driver.get(f"{WIDGETS_URL}/javascript_alerts")

        page.click((By.CSS_SELECTOR, "button[onclick='jsPrompt()']"))
        page.accept_prompt("automation")

        result = page.get_text((By.ID, "result"))
        assert result == "You entered: automation", (
            f"Prompt input text was not reflected in the result, got: {result!r}"
        )


class TestMultipleWindows:
    def test_switch_to_new_window_and_back(self, driver):
        page = BasePage(driver)
        driver.get(f"{WIDGETS_URL}/windows")

        original_handle = driver.current_window_handle
        # Capture handles BEFORE the action that opens the new window/tab —
        # see the docstring on switch_to_new_window for why order matters.
        original_handles = driver.window_handles

        page.click((By.LINK_TEXT, "Click Here"))
        page.switch_to_new_window(original_handles)

        assert driver.title == "New Window", (
            f"Expected to be focused on the new tab, but title was: {driver.title!r}"
        )
        heading = page.get_text((By.CSS_SELECTOR, "h3"))
        assert heading == "New Window"

        # Clean up: close the extra tab and return focus to the original —
        # leaving stray windows open is one way parallel/serial test runs
        # bleed state into each other.
        page.close_and_switch_back(original_handle)
        assert driver.title == "The Internet"


class TestFileUpload:
    def test_upload_file(self, driver):
        page = BasePage(driver)
        driver.get(f"{WIDGETS_URL}/upload")

        # A small, checked-in dummy file — see tests/fixtures/sample_upload.txt.
        # If you need to regenerate it, any small text file works; the test
        # only asserts on the uploaded FILE NAME, not its contents.
        upload_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "fixtures", "sample_upload.txt")
        )
        assert os.path.exists(upload_path), (
            f"Fixture file missing: {upload_path}. See tests/fixtures/sample_upload.txt"
        )

        # send_keys populates the <input type="file"> directly — no OS
        # file-picker dialog ever appears, so this works headlessly and on
        # Grid nodes with no display attached.
        page.upload_file((By.ID, "file-upload"), upload_path)
        page.click((By.ID, "file-submit"))

        uploaded_file_name = page.get_text((By.ID, "uploaded-files"))
        assert uploaded_file_name == "sample_upload.txt", (
            f"Expected uploaded file name to echo back, got: {uploaded_file_name!r}"
        )
