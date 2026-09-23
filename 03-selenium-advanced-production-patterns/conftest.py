"""
conftest.py — shared pytest fixtures and hooks for the advanced Selenium suite.

Three ideas are demonstrated here (each explained in depth in README.md):

  1. BROWSER FACTORY — `build_driver()` is the single place that knows how
     to construct a Chrome/Firefox/Edge driver, either locally (via
     webdriver-manager) or remotely (via `webdriver.Remote` against a
     Selenium Grid hub). Tests and page objects never import
     `selenium.webdriver.Chrome` etc. directly.

  2. FUNCTION-SCOPED `driver` FIXTURE — deliberately scoped to a single
     test, not the session or module. See "Why function-scoped drivers
     matter for parallel execution" in README.md: a shared driver would
     leak cookies/localStorage/open alerts between tests and would break
     safely running tests in parallel with pytest-xdist.

  3. FAILURE DIAGNOSTICS HOOK — `pytest_runtest_makereport` captures a
     screenshot, the page source, and (where supported) browser console
     logs the moment a test fails, and attaches the screenshot to the
     pytest-html report. This is what makes a CI failure debuggable without
     first reproducing it locally.
"""
import re
import time
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from config import config


# ---------------------------------------------------------------------------
# CLI options — let a run override .env values without editing files, e.g.:
#   pytest --browser=firefox --headless
#   pytest --grid-url=http://localhost:4444/wd/hub -n auto
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--browser", action="store", default=None,
        help="chrome | firefox | edge (overrides the BROWSER env var)",
    )
    parser.addoption(
        "--headless", action="store_true", default=None,
        help="Run the browser headlessly (overrides the HEADLESS env var)",
    )
    parser.addoption(
        "--grid-url", action="store", default=None,
        help="Selenium Grid hub URL, e.g. http://localhost:4444/wd/hub "
             "(overrides the SELENIUM_GRID_URL env var)",
    )


def _resolve(cli_value, config_value):
    """CLI flag wins when explicitly provided; otherwise fall back to config.py."""
    return cli_value if cli_value not in (None, False) else config_value


# ---------------------------------------------------------------------------
# Browser factory
# ---------------------------------------------------------------------------

def _build_chrome_options(headless: bool) -> ChromeOptions:
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    # These aren't cosmetic — without them Chrome regularly crashes inside
    # Docker/CI containers (no sandbox namespace, tiny /dev/shm default).
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Turn on browser-console log capture so failures can be diagnosed
    # without re-running with devtools open.
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    return options


def _build_firefox_options(headless: bool) -> FirefoxOptions:
    options = FirefoxOptions()
    if headless:
        options.add_argument("-headless")
    return options


def _build_edge_options(headless: bool) -> EdgeOptions:
    options = EdgeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return options


_OPTION_BUILDERS = {
    "chrome": _build_chrome_options,
    "firefox": _build_firefox_options,
    "edge": _build_edge_options,
}


def build_driver(browser: str, headless: bool, grid_url: str = ""):
    """
    The single place that knows how to construct a WebDriver.

    Centralizing this means adding a new browser or changing a stability
    flag is a one-line, one-function change instead of a find-and-replace
    across the suite — and switching between local execution and a remote
    Selenium Grid is a *config* change, not a code change (see the
    `grid_url` branch below and docker-compose.yml).
    """
    browser = browser.lower()
    if browser not in _OPTION_BUILDERS:
        raise ValueError(
            f"Unsupported browser '{browser}'. Choose from {list(_OPTION_BUILDERS)}."
        )

    options = _OPTION_BUILDERS[browser](headless)

    if grid_url:
        # Remote execution against Selenium Grid (docker-compose.yml) or CI.
        # Test code and page objects are IDENTICAL whether this branch runs
        # or the local branch below does — that's what makes Grid a drop-in
        # scalability upgrade rather than a parallel test suite to maintain.
        return webdriver.Remote(command_executor=grid_url, options=options)

    # Local execution: webdriver-manager downloads and caches the driver
    # binary matching the installed browser version, so nobody on the team
    # (or in CI) has to hand-manage chromedriver/geckodriver/msedgedriver.
    if browser == "chrome":
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    if browser == "firefox":
        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)
    # browser == "edge"
    service = EdgeService(EdgeChromiumDriverManager().install())
    return webdriver.Edge(service=service, options=options)


@pytest.fixture
def driver(request):
    """
    Function-scoped WebDriver fixture — one fresh browser per test.

    This must stay function-scoped:
      - pytest-xdist runs each test in a worker process, but WITHIN a
        worker a session/module-scoped driver would still leak cookies,
        localStorage, and open alerts between tests sharing it.
      - A crashed or hung browser in one test can't take the rest of the
        suite down with it.
      - Tests remain order-independent and safely re-runnable (idempotent),
        which is also what makes --reruns (pytest-rerunfailures) safe to use.
    The cost is per-test browser startup time; parallelism (`pytest -n
    auto`) and Grid (multiple node containers) are how that cost is paid
    back — see README.md.
    """
    browser = _resolve(request.config.getoption("--browser"), config.browser)
    headless = _resolve(request.config.getoption("--headless"), config.headless)
    grid_url = _resolve(request.config.getoption("--grid-url"), config.selenium_grid_url)

    drv = build_driver(browser, headless, grid_url)
    # We standardize on EXPLICIT waits everywhere (see pages/base_page.py),
    # so implicit wait stays at 0 — mixing the two causes unpredictable,
    # hard-to-debug wait times.
    drv.implicitly_wait(0)

    yield drv

    drv.quit()


# ---------------------------------------------------------------------------
# Failure diagnostics: screenshot + page source + console log on failure.
# ---------------------------------------------------------------------------

def _safe_name(name: str) -> str:
    """Turn a pytest nodeid into a filesystem-safe directory name."""
    return re.sub(r"[^\w\-.]", "_", name)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Standard pytest pattern for "act on the outcome once the test body has
    run." We let the test execute normally, inspect the report, and if the
    `call` phase failed, pull whatever the `driver` fixture is currently
    pointing at and dump diagnostics to `artifacts/<test-name>/`.

    This runs regardless of whether the failure is later masked by
    pytest-rerunfailures — every failed attempt gets its own timestamped
    artifact set, which is exactly what you want when diagnosing flakiness.
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if report.when != "call" or not report.failed:
        return

    driver_instance = item.funcargs.get("driver")
    if driver_instance is None:
        return  # this test doesn't use the `driver` fixture — nothing to capture

    out_dir = Path(config.artifacts_dir) / _safe_name(item.nodeid)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")

    screenshot_path = out_dir / f"{timestamp}.png"
    source_path = out_dir / f"{timestamp}.html"
    console_log_path = out_dir / f"{timestamp}.console.log"

    try:
        driver_instance.save_screenshot(str(screenshot_path))
    except Exception as exc:  # noqa: BLE001 — diagnostics must never crash the run
        print(f"[artifact capture] screenshot failed: {exc}")
        screenshot_path = None

    try:
        source_path.write_text(driver_instance.page_source, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"[artifact capture] page source capture failed: {exc}")

    try:
        # Only Chromium-based drivers reliably expose the browser log API;
        # Firefox/Edge configurations can raise here, so degrade gracefully
        # instead of failing the whole diagnostics capture over one part.
        logs = driver_instance.get_log("browser")
        lines = [f"[{entry.get('level')}] {entry.get('message')}" for entry in logs]
        console_log_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"[artifact capture] console log capture unavailable: {exc}")

    print(f"[artifact capture] saved diagnostics to {out_dir}/")

    # Attach the screenshot (and a page-source excerpt) into the pytest-html
    # report, if pytest-html is active for this run (--html=report.html).
    pytest_html = item.config.pluginmanager.getplugin("html")
    if pytest_html is not None and screenshot_path is not None:
        extra = getattr(report, "extra", [])
        try:
            extra.append(pytest_html.extras.image(str(screenshot_path)))
            extra.append(
                pytest_html.extras.text(
                    driver_instance.page_source[:5000], name="page_source_excerpt"
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[artifact capture] could not attach extras to HTML report: {exc}")
        report.extra = extra
