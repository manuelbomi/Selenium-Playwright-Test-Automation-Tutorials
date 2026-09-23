"""
conftest.py

pytest-playwright ships fully isolated, function-scoped `page`, `context`,
and `browser` fixtures out of the box -- every test gets a brand-new
BrowserContext (its own cookies/localStorage/session storage) and a fresh
Page, torn down automatically when the test ends. See README "Built-in
Fixtures" for why that matters.

Contrast with Tutorial 2/3: Selenium's conftest.py had to hand-write a
`driver` fixture that created a WebDriver instance, yielded it, and then
explicitly called `driver.quit()` in teardown -- and get that right for
every test, every browser. Here, there's nothing to hand-write for that;
this file exists almost entirely to configure `base_url`.
"""

import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    """
    Override pytest-playwright's `base_url` fixture so every `page.goto()`
    call in this suite can use a path relative to saucedemo's root
    ("/", "/inventory.html", ...) instead of a hardcoded full URL.

    Why this is cleaner than hardcoding the URL in every test/page object:
      - One line to change if you ever point this suite at a staging
        environment, a different demo instance, or a locally-hosted copy.
      - Test and page-object code reads shorter and stays focused on
        *behavior* ("go to the login page") rather than *infrastructure*
        (which host you're talking to).
      - It's the same value pytest-playwright uses to resolve relative
        URLs for you automatically -- no custom navigate-and-prefix helper
        needed.
    """
    return "https://www.saucedemo.com"
