# CLAUDE.md — Project Conventions for This Automation Repo

This file is read automatically by Claude Code at the start of every session in
this repo. It is instructions for the agent, not marketing copy — keep it
short, concrete, and enforceable. Copy this pattern into your own Selenium /
Playwright repos and adjust the paths.

## What this repo is

A Python test automation suite covering both Selenium and Playwright, built
across Tutorials 1–5 of this series:

- `02-selenium-fundamentals/` — Selenium WebDriver basics, Page Object Model
- `03-selenium-advanced-production-patterns/` — POM at scale, parallel
  execution, Dockerized Selenium Grid, CI
- `04-playwright-fundamentals/` — Playwright basics, Page Object Model,
  `pytest-playwright`
- `05-playwright-advanced-production-patterns/` — network mocking,
  `storage_state` auth reuse, visual testing, sharding, Docker/CI

## Directory conventions

- **Page Objects live under `pages/`** in each tutorial folder (e.g.
  `04-playwright-fundamentals/pages/`, `05-playwright-advanced-production-patterns/pages/`).
  One class per page/flow. Do not put assertions inside Page Objects — they
  expose actions and locators only; assertions belong in test files.
- **Tests live under `tests/`** in each tutorial folder, one file per feature
  area, named `test_<feature>.py` (e.g. `test_checkout.py`, `test_login.py`).
- **Fixtures live in `conftest.py`** at the tests root of each tutorial
  folder. Reuse existing fixtures (`page`, `browser_context_args`,
  `authenticated_page`, etc.) instead of creating ad hoc setup inside a test.
- **Locators**: prefer Playwright's role/text/label-based locators
  (`get_by_role`, `get_by_label`, `get_by_test_id`) and Selenium's
  `By.CSS_SELECTOR` / accessible-name-based strategies over brittle CSS/XPath
  tied to styling classes or generated IDs. This matches the locator
  guidance from Tutorial 4.

## Required agent workflow

1. Before editing, read the relevant `pages/` and `conftest.py` files in the
   tutorial folder you are working in to match existing naming and structure.
2. Write or modify test code following the existing Page Object pattern —
   do not introduce a new pattern (e.g. inline selectors in tests, or a
   different fixture style) without being asked.
3. **Always run the relevant subfolder's test suite before considering a
   task done.** Example: after changing anything under
   `05-playwright-advanced-production-patterns/`, run:
   ```
   cd 05-playwright-advanced-production-patterns
   pytest -q
   ```
   Do not report a task complete on the basis of code that "looks right" —
   run it.
4. If a test fails, read the actual failure output (and, for Playwright, the
   HTML report / trace if one was generated) before proposing a fix. Do not
   guess at a fix without evidence from a failure.
5. Summarize what changed and why in your final response. Do not commit or
   push on your own — a human reviews and merges every change via normal PR
   review.

## Hard rules

- **Never commit `.env`, `state.json`, `storage_state.json`, or anything
  under `auth_setup/` output directories.** These contain credentials or
  session tokens. Check `.gitignore` covers them before adding new files of
  this shape.
- **Never hardcode credentials in test code.** Read them from environment
  variables populated from `.env` (which is itself gitignored).
- **Never use `time.sleep()` for synchronization.** Use Playwright's
  auto-waiting locators/assertions (`expect(locator).to_be_visible()`, etc.)
  or Selenium's explicit `WebDriverWait` + expected_conditions. A bare sleep
  is treated as a bug, not a fix.
- **Never point a test run at a production URL or use production
  credentials**, even temporarily "just to check something." Only
  test/staging environments and test-only accounts are in scope for
  automated runs, whether run by a human or by an agent.
- **Do not widen CI permissions or add new MCP servers to `.mcp.json`
  without flagging it explicitly** in your summary — both are reviewed like
  any other dependency or access change.

## MCP servers available in this repo

- `playwright` (`@playwright/mcp`) — lets the agent drive a real browser
  (navigate, click, take an accessibility snapshot) to explore an app or
  reproduce a bug interactively. This is for **exploration and diagnosis**,
  not a substitute for writing committed Playwright/Selenium test code. Any
  selector or flow discovered this way should be turned into a Page Object
  change and a test, reviewed like any other code change.
