"""
Standalone script: authenticate against saucedemo.com ONCE and persist the
resulting browser storage state (cookies + localStorage) to auth_setup/state.json.

WHY THIS EXISTS
----------------
saucedemo's "session" is just a localStorage flag set after a successful
login form submit. Re-running that UI flow before every single test is slow
and adds an extra point of flakiness that has nothing to do with what most
tests actually want to verify (cart behavior, checkout, sorting, etc.).

By logging in once here and handing the saved storage_state to Playwright's
`context` fixture (see conftest.py's `authenticated_context` fixture), every
test can start already authenticated, straight on the inventory page. This
is one of the most impactful production techniques in Playwright: it turns
"log in" from an O(n) cost (n = number of tests) into an O(1) cost.

USAGE
-----
Run manually to (re)generate the state file:

    python auth_setup/generate_auth_state.py

It is also invoked automatically by conftest.py the first time a test needs
`authenticated_context` / `authenticated_page` and auth_setup/state.json is
missing, so a fresh clone of this repo "just works" with no manual step.

SECURITY NOTE
-------------
auth_setup/state.json contains live session data (cookies/localStorage).
Treat it like a credential file: it MUST stay in .gitignore and never be
committed. On a real (non-demo) application, anyone holding that file could
use it to resume an authenticated session -- this is the habit that matters,
even though saucedemo itself is a throwaway public demo.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://www.saucedemo.com")
SAUCE_USERNAME = os.getenv("SAUCE_USERNAME", "standard_user")
SAUCE_PASSWORD = os.getenv("SAUCE_PASSWORD", "secret_sauce")

# state.json lives next to this script so conftest.py can find it with a
# path relative to __file__, regardless of the directory pytest is run from.
STATE_PATH = Path(__file__).parent / "state.json"


def generate_auth_state() -> None:
    """Log in through the real UI once and save the resulting session to disk."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        # base_url lets the rest of the script use relative goto() calls,
        # matching how tests in this suite navigate.
        context = browser.new_context(base_url=BASE_URL)
        page = context.new_page()

        page.goto("/")
        page.get_by_placeholder("Username").fill(SAUCE_USERNAME)
        page.get_by_placeholder("Password").fill(SAUCE_PASSWORD)
        page.get_by_role("button", name="Login").click()

        # Fail loudly if login didn't actually succeed -- saving the state of
        # a FAILED login would silently poison every test that depends on it,
        # and the resulting failures would look nothing like an auth problem.
        page.wait_for_url("**/inventory.html", timeout=10_000)

        context.storage_state(path=str(STATE_PATH))
        print(f"Saved authenticated storage state to: {STATE_PATH}")

        context.close()
        browser.close()


if __name__ == "__main__":
    generate_auth_state()
