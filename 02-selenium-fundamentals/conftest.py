"""
Shared pytest fixtures and hooks for the Selenium fundamentals suite.

Living here (rather than in each test file) means every test module in
tests/ gets the `driver` fixture and the failure-screenshot hook for free —
this is the standard pytest pattern for cross-cutting test infrastructure.
"""

import os
from datetime import datetime

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")


def pytest_addoption(parser):
    """
    Adds `--headless` as a pytest CLI flag.

    Headless is opt-in (not the default) so a junior engineer's first local
    run shows a visible browser — seeing the test drive the UI is one of the
    fastest ways to build a mental model of what Selenium is doing. CI
    pipelines pass --headless because there's no display and headless is
    faster/lighter on shared runners.
    """
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run Chrome in headless mode (no visible browser window).",
    )


@pytest.fixture(scope="function")
def driver(request):
    """
    Builds a fresh Chrome WebDriver for each test and quits it afterwards.

    Function scope (a new browser per test) trades some speed for the thing
    that matters most in a test suite: isolation. If tests shared one driver,
    cookies/localStorage/open tabs from one test could leak into the next
    and cause failures that have nothing to do with the code under test.
    """
    options = Options()

    # Start maximized (not headless) so elements aren't hidden by a small
    # viewport — a common source of "element not clickable" flakiness that
    # has nothing to do with the app under test.
    options.add_argument("--start-maximized")

    if request.config.getoption("--headless"):
        # "--headless=new" is Chrome's modern headless mode — closer in
        # rendering behavior to a real window than the legacy headless mode,
        # which reduces "works headed, fails headless" surprises in CI.
        options.add_argument("--headless=new")
        # No real window to maximize into when headless, so set an explicit
        # size instead — without this, headless defaults to a small viewport
        # that can hide elements and change responsive layout behavior.
        options.add_argument("--window-size=1920,1080")

    # Common flags for running Chrome in containers/CI (harmless locally).
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    # webdriver-manager downloads/caches the ChromeDriver binary that matches
    # the installed Chrome version, so nobody has to manually manage
    # driver binaries or fight version-mismatch errors (see Tutorial 1).
    service = Service(ChromeDriverManager().install())
    chrome_driver = webdriver.Chrome(service=service, options=options)

    yield chrome_driver

    # Runs even if the test fails/raises, since the code after `yield` in a
    # fixture is a teardown block — this is what prevents orphaned browser
    # processes from piling up across a test run.
    chrome_driver.quit()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """
    Saves a screenshot when a test fails, named after the failing test.

    A screenshot taken *at the moment of failure* is far more useful for
    debugging than one taken afterward — by the time a human investigates,
    the browser (if still open at all) has moved on. Hooking into report
    generation is what lets us capture the DOM state exactly as it was when
    the assertion failed.
    """
    outcome = yield
    report = outcome.get_result()

    # pytest calls this hook for setup, call, and teardown phases of every
    # test. We only care about the "call" phase — that's the actual test
    # body, as opposed to fixture setup/teardown.
    if report.when != "call" or not report.failed:
        return

    # The `driver` fixture's value, if the failing test used it, lives in
    # item.funcargs. Tests that don't use `driver` simply won't have it —
    # guard with .get() so the hook never breaks a non-UI test's reporting.
    web_driver = item.funcargs.get("driver")
    if web_driver is None:
        return

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # Timestamp avoids overwriting the previous failure's screenshot when
    # the same test is re-run (e.g. during a flaky-test investigation).
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_test_name = item.name.replace("/", "_").replace("::", "_")
    screenshot_path = os.path.join(
        SCREENSHOT_DIR, f"{safe_test_name}_{timestamp}.png"
    )

    try:
        web_driver.save_screenshot(screenshot_path)
    except Exception as exc:
        # A screenshot failure (e.g. browser already crashed/closed) should
        # never mask the real test failure — log and move on.
        print(f"Could not capture failure screenshot: {exc}")
