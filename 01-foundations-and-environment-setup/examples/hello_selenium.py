"""
hello_selenium.py
------------------
A minimal, runnable "Hello World" for Selenium WebDriver.

This is NOT a pytest test -- it's a plain script you run directly with
`python hello_selenium.py` so you can see, line by line, what Selenium is
doing before we introduce the pytest framework in Tutorial 2.

What this script does:
    1. Spins up a real Chrome browser window, using webdriver-manager to
       fetch/match the correct chromedriver binary automatically.
    2. Navigates to https://www.saucedemo.com/ (the public demo e-commerce
       site used throughout this tutorial series).
    3. Asserts the page title is what we expect.
    4. Cleans up the browser process in a `finally` block, guaranteeing the
       browser closes even if an assertion fails or an exception is raised.

Run it with:
    python hello_selenium.py
"""

# selenium.webdriver is the entry point for launching and controlling browsers.
from selenium import webdriver

# ChromeService wraps the chromedriver executable process that Selenium
# talks to under the hood (see README.md for the full WebDriver architecture
# explanation: client bindings -> driver executable -> browser).
from selenium.webdriver.chrome.service import Service as ChromeService

# webdriver-manager downloads (and caches) the chromedriver binary that
# matches your installed Chrome version, so you never have to manually
# download a driver executable, put it on PATH, or update it when Chrome
# auto-updates. This is why we install it alongside selenium.
from webdriver_manager.chrome import ChromeDriverManager

# The public demo site used across this entire tutorial series. It's a
# stable, intentionally-simple e-commerce site built for practicing
# automation, so it's safe to hit repeatedly without rate limits or
# real-world side effects.
SAUCE_DEMO_URL = "https://www.saucedemo.com/"


def run_hello_selenium() -> None:
    """Launch Chrome, visit SauceDemo, verify the title, then clean up."""

    # driver starts as None so the `finally` block below can safely check
    # "did we actually get a driver object?" even if ChromeDriverManager()
    # or webdriver.Chrome() itself raises before assignment completes.
    driver = None

    try:
        # ChromeDriverManager().install() returns a filesystem path to a
        # chromedriver binary version-matched to your local Chrome install.
        # The first run downloads it; later runs reuse a local cache, so
        # this is fast after the first execution.
        service = ChromeService(ChromeDriverManager().install())

        # This is the actual "launch a browser" call. Under the hood,
        # Selenium starts the chromedriver process (the "driver executable"
        # in the WebDriver architecture), which in turn launches and
        # controls a real Chrome browser window.
        driver = webdriver.Chrome(service=service)

        # Navigate the browser to the target URL. This blocks until the
        # browser reports the initial page load event has fired.
        driver.get(SAUCE_DEMO_URL)

        # SauceDemo's <title> tag reads "Swag Labs" -- checking it is a
        # quick smoke-test that the page actually loaded the right site
        # (as opposed to a network error page, a redirect, etc.).
        assert "Swag Labs" in driver.title, (
            f"Expected 'Swag Labs' in page title, got: {driver.title!r}"
        )

        print("SUCCESS: Selenium launched Chrome and loaded SauceDemo correctly.")
        print(f"Page title was: {driver.title!r}")

    finally:
        # Cleanup ALWAYS runs, whether the try block succeeded, raised an
        # assertion error, or raised any other exception. Forgetting this
        # step is one of the most common beginner mistakes in Selenium: it
        # leaves orphaned chromedriver + Chrome processes running in the
        # background, which silently eats memory and can eventually make
        # your machine (or CI runner) grind to a halt.
        if driver is not None:
            driver.quit()  # Closes the browser AND terminates the driver process.


if __name__ == "__main__":
    # The `if __name__ == "__main__":` guard means this function only runs
    # when you execute this file directly (`python hello_selenium.py`), not
    # if it's ever imported as a module elsewhere. Good habit for any script.
    run_hello_selenium()
