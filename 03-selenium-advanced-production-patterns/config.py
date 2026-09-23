"""
config.py — centralized configuration for the test suite.

WHY THIS FILE EXISTS
---------------------
Hardcoding URLs, browser choice, or credentials directly in test files means
every environment change (local -> CI -> staging) requires editing test
code, and it invites secrets being committed to git history. This module is
the ONLY place that reads environment variables; every other module
(conftest.py, page objects, tests) imports `config` from here instead of
calling os.environ / os.getenv directly. That gives us one seam to swap
values per environment, and one place to audit for accidental secrets.

Precedence: real OS/CI environment variables > values in a local `.env`
file > hardcoded defaults below. `load_dotenv()` does NOT override
variables that are already set in the process environment, which is
exactly what we want: in CI, secrets are injected as real env vars and
must win over anything a stray .env file might contain.
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load a local .env file if one exists (no-op, no error, if it doesn't —
# this keeps CI, Docker, and fresh clones working without a .env present).
load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    """Parse a boolean-ish environment variable ('true', '1', 'yes', 'on')."""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    """
    Immutable snapshot of test configuration, resolved once at import time.

    Frozen on purpose: configuration should not silently change mid-run.
    If a test needs a different value, it should build its own driver /
    pass an override explicitly rather than mutating shared config.
    """

    # --- Applications under test -----------------------------------------
    base_url: str = os.getenv("BASE_URL", "https://www.saucedemo.com")
    widgets_url: str = os.getenv("WIDGETS_URL", "https://the-internet.herokuapp.com")

    # --- Browser selection --------------------------------------------------
    browser: str = os.getenv("BROWSER", "chrome").lower()
    headless: bool = field(default_factory=lambda: _bool_env("HEADLESS", False))

    # --- Credentials -----------------------------------------------------
    # NEVER hardcode these in test code. saucedemo's "standard_user" is a
    # public demo credential, but we treat it like a real secret here so
    # the pattern is identical to what you'd do with a production login:
    # read from env vars, which in CI are populated from encrypted secrets.
    sauce_username: str = os.getenv("SAUCE_USERNAME", "standard_user")
    sauce_password: str = os.getenv("SAUCE_PASSWORD", "secret_sauce")

    # --- Waiting -----------------------------------------------------------
    explicit_wait: int = int(os.getenv("EXPLICIT_WAIT", "10"))

    # --- Remote execution (Selenium Grid / Docker / CI) ---------------------
    # Empty string means "build a local driver". A non-empty URL (e.g.
    # http://localhost:4444/wd/hub) switches the browser factory in
    # conftest.py to webdriver.Remote — see docker-compose.yml.
    selenium_grid_url: str = os.getenv("SELENIUM_GRID_URL", "")

    # --- Diagnostics ---------------------------------------------------------
    artifacts_dir: str = os.getenv("ARTIFACTS_DIR", "artifacts")


# Module-level singleton — import this, don't instantiate Config() yourself,
# so every module in the suite agrees on the same resolved configuration.
config = Config()
