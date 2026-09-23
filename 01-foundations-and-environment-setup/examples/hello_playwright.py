"""
hello_playwright.py
--------------------
A minimal, runnable "Hello World" for Playwright's sync API.

Like hello_selenium.py, this is a plain script (not a pytest test) so you
can read it top-to-bottom and see exactly what Playwright does before we
introduce pytest fixtures in Tutorial 4.

What this script does:
    1. Starts the Playwright driver process and launches a Chromium browser.
    2. Opens a new isolated browser context and a new page.
    3. Navigates to https://www.saucedemo.com/ and asserts the page title.
    4. Cleans up automatically via a `with` block -- no manual driver.quit().

Key difference from Selenium (see hello_selenium.py):
    Selenium needs a separate driver executable (chromedriver) that speaks
    the WebDriver HTTP protocol to the browser, and you must manually call
    driver.quit() in a finally block to clean it up. Playwright ships a
    single library that talks directly to the browser over CDP
    (Chrome DevTools Protocol) / WebSocket -- no separate driver binary to
    manage -- and its `with sync_playwright() as p:` context manager
    guarantees cleanup automatically when the block exits, even on error.
    You still close the browser explicitly below for clarity, but you do
    NOT need a try/finally to guarantee the Playwright driver process itself
    shuts down cleanly -- the `with` block handles that.

Run it with:
    python hello_playwright.py
"""

# sync_playwright is the synchronous (blocking, non-async) entry point into
# Playwright. It's the simplest way to start for engineers new to browser
# automation; Playwright also offers an async API for use inside asyncio
# applications, which we won't need in this tutorial series.
from playwright.sync_api import sync_playwright

# Same public demo site used across this tutorial series and in
# hello_selenium.py, so you can directly compare the two frameworks against
# an identical target.
SAUCE_DEMO_URL = "https://www.saucedemo.com/"


def run_hello_playwright() -> None:
    """Launch Chromium, visit SauceDemo, verify the title, then clean up."""

    # `with sync_playwright() as p:` starts the Playwright driver process
    # and guarantees it's shut down when this block exits -- comparable to
    # what Selenium's `finally: driver.quit()` does manually, but automatic.
    with sync_playwright() as p:
        # p.chromium / p.firefox / p.webkit are the three browser engines
        # Playwright supports out of the box. launch() starts a real
        # browser process. headless=False pops open a visible window so
        # you can watch it work -- flip to True (the default) once you
        # trust your scripts and want faster, invisible runs (e.g. in CI).
        browser = p.chromium.launch(headless=False)

        # A "browser context" is an isolated, incognito-like session: its
        # own cookies, local storage, and cache, completely separate from
        # any other context created from the same browser process. This is
        # what gives Playwright tests strong isolation without paying the
        # cost of launching a brand-new browser process per test (see
        # README.md for the full browser/context/page model explanation).
        context = browser.new_context()

        # A "page" is a single browser tab living inside that context.
        # A context can hold multiple pages (multi-tab scenarios), which
        # we'll use in later tutorials.
        page = context.new_page()

        # Navigate to the target URL. Playwright auto-waits for the page's
        # load lifecycle to reach a stable state before returning control,
        # which is part of why Playwright scripts need far fewer explicit
        # waits than equivalent Selenium scripts (see the comparison table
        # in README.md).
        page.goto(SAUCE_DEMO_URL)

        # page.title() returns the current <title> tag content. SauceDemo's
        # title is "Swag Labs" -- same assertion as the Selenium version,
        # so the two scripts are directly comparable.
        title = page.title()
        assert "Swag Labs" in title, (
            f"Expected 'Swag Labs' in page title, got: {title!r}"
        )

        print("SUCCESS: Playwright launched Chromium and loaded SauceDemo correctly.")
        print(f"Page title was: {title!r}")

        # Explicit close for clarity and to free the OS-level browser
        # process promptly. Even if you omitted this line, exiting the
        # `with sync_playwright() as p:` block still tears down the
        # Playwright driver connection cleanly -- unlike Selenium, there's
        # no risk of an orphaned driver process left over if you forget.
        browser.close()


if __name__ == "__main__":
    run_hello_playwright()
