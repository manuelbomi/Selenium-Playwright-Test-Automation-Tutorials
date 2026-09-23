"""
Shared pytest fixtures for this tutorial's suite.

Two things live here:
  1. `base_url` / `browser_context_args` -- so every test can use relative
     paths like page.goto("/inventory.html") instead of hardcoding the
     domain, and so the target URL is driven entirely by .env / CI env vars.
  2. `authenticated_context` / `authenticated_page` -- the storage_state
     reuse pattern. These load the pre-authenticated session saved by
     auth_setup/generate_auth_state.py so tests can skip the login UI
     entirely (see tests/test_authenticated_flow.py).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env once, at collection time, before any fixture reads os.environ.
load_dotenv()

AUTH_SETUP_DIR = Path(__file__).parent / "auth_setup"
STATE_PATH = AUTH_SETUP_DIR / "state.json"


def pytest_configure(config: pytest.Config) -> None:
    # Register the custom marker used in tests/test_visual.py so pytest
    # doesn't warn about an "unknown marker" -- keeps `pytest --strict-markers`
    # (a good production default) usable in this repo.
    config.addinivalue_line(
        "markers", "visual: visual regression tests (screenshot comparisons)"
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    """
    Single source of truth for the app under test's URL.

    Reads BASE_URL from .env / the environment so switching between local,
    staging, and prod targets in CI is a config change, not a code change.
    """
    return os.getenv("BASE_URL", "https://www.saucedemo.com")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, base_url: str) -> dict:
    """
    Override pytest-playwright's default context args to inject base_url.

    This is what makes plain, unauthenticated tests (test_network_mocking.py,
    test_visual.py) able to call page.goto("/") instead of the full URL --
    it applies to the default `context`/`page` fixtures pytest-playwright
    already provides, not just our custom authenticated ones below.
    """
    return {**browser_context_args, "base_url": base_url}


def _ensure_auth_state_exists() -> None:
    """
    Generate auth_setup/state.json on demand if it isn't already there.

    Running this as a subprocess (rather than importing and calling the
    function in-process) keeps the auth setup's own Playwright driver
    lifecycle fully isolated from the test run's -- avoids any risk of two
    sync_playwright() managers interfering with each other.
    """
    if not STATE_PATH.exists():
        subprocess.run(
            [sys.executable, str(AUTH_SETUP_DIR / "generate_auth_state.py")],
            check=True,
        )


@pytest.fixture
def authenticated_context(browser, base_url: str):
    """
    A browser context that starts already logged in to saucedemo.com.

    This is the payoff of the storage_state technique: login happens once
    (outside the test, via auth_setup/generate_auth_state.py) and every test
    that needs an authenticated session just loads the saved cookies/
    localStorage here instead of re-running the login UI flow.
    """
    _ensure_auth_state_exists()
    context = browser.new_context(storage_state=str(STATE_PATH), base_url=base_url)
    yield context
    context.close()


@pytest.fixture
def authenticated_page(authenticated_context):
    """Convenience fixture: a single page inside an authenticated_context."""
    page = authenticated_context.new_page()
    yield page
    page.close()
