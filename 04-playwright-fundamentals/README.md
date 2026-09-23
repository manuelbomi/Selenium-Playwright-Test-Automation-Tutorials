# Tutorial 4: Playwright Fundamentals — Setup, Locators & Auto-Waiting Explained

Part 4 of the **Selenium & Playwright Test Automation Tutorials** series.

This tutorial teaches the same core skills as [Tutorial 2 (Selenium Fundamentals)](../02-selenium-fundamentals/README.md), but in **Playwright** using `pytest-playwright`, against the same kind of target: a real, runnable test suite against the public demo site [saucedemo.com](https://www.saucedemo.com/). The structure deliberately mirrors Tutorial 2 so you can compare the two frameworks section by section, decision by decision.

If you haven't finished [Tutorial 1](../01-foundations-and-environment-setup/README.md) (environment setup + a Playwright "Hello World" script), do that first.

---

## Table of Contents

1. [Playwright's Architecture: Browser → BrowserContext → Page](#1-playwrights-architecture-browser--browsercontext--page)
2. [Installing pytest-playwright](#2-installing-pytest-playwright)
3. [Locators: Choosing the Right One, in Order](#3-locators-choosing-the-right-one-in-order)
4. [Auto-Waiting Explained](#4-auto-waiting-explained)
5. [Actions: click, fill, check, select_option, hover](#5-actions-click-fill-check-select_option-hover)
6. [Assertions: Why `expect()` Beats a Bare `assert`](#6-assertions-why-expect-beats-a-bare-assert)
7. [`playwright codegen`: Bootstrapping Locators](#7-playwright-codegen-bootstrapping-locators)
8. [The Trace Viewer for Debugging](#8-the-trace-viewer-for-debugging)
9. [Built-in Fixtures: `page`, `context`, `browser`](#9-built-in-fixtures-page-context-browser)
10. [Page Object Model in Playwright](#10-page-object-model-in-playwright)
11. [Project Structure](#11-project-structure)
12. [Running the Tests](#12-running-the-tests)
13. [Side-by-Side: Selenium vs Playwright](#13-side-by-side-selenium-vs-playwright)
14. [What's Next](#14-whats-next)

---

## 1. Playwright's Architecture: Browser → BrowserContext → Page

Playwright's object model has three layers, and understanding them is the single most useful mental model for everything else in this tutorial:

```
Browser
 └── BrowserContext   (isolated "incognito-like" session: its own cookies, localStorage, sessionStorage, cache)
      └── Page         (a single tab/window inside that context)
           └── Locator (a lazy, auto-waiting reference to element(s) on the page)
```

- **Browser** — a single launched instance of Chromium, Firefox, or WebKit. Launching a browser is relatively expensive, so you typically launch *one* per test session and reuse it.
- **BrowserContext** — this is Playwright's key isolation unit, and it's the concept Selenium doesn't really have an equivalent for. A context is like a fresh incognito profile: its own cookies, storage, permissions, and viewport, completely walled off from every other context in the same browser process. Creating a new context is *cheap* (milliseconds), much cheaper than launching a whole new browser process.
- **Page** — a single tab within a context. Most of your test code interacts with a `Page`.

**Why this matters for testing:** in Selenium, true test isolation usually meant a new WebDriver session per test — a new browser *process* — which is slow. In Playwright, you can spin up a new `BrowserContext` (and `Page`) per test from a *single shared browser process*, giving each test its own cookies/storage/session with none of the cross-test contamination risk, at a fraction of the cost. This is exactly what `pytest-playwright`'s built-in fixtures do for you automatically (see [section 9](#9-built-in-fixtures-page-context-browser)) — every test function gets its own fresh, isolated context and page, which is what makes safe test parallelization straightforward in Playwright.

---

## 2. Installing pytest-playwright

```bash
pip install -r requirements.txt
playwright install
```

`requirements.txt` in this folder pulls in `pytest`, `pytest-playwright`, and `playwright`. `playwright install` then downloads the actual browser binaries (Chromium, Firefox, WebKit) that this version of the `playwright` package was built and tested against.

**Contrast with Selenium (Tutorial 2):** Selenium requires you to separately manage a *driver binary* (chromedriver, geckodriver, ...) that matches your installed browser version — historically a common source of "works on my machine" breakage, which is why Tutorial 2 covered `webdriver-manager` to automate that matching. Playwright sidesteps the whole problem: each `playwright` package version bundles/pins compatible browser builds, and `playwright install` fetches exactly those. There's no separate driver-to-browser version matrix to maintain, and no system-installed browser required at all — the browsers Playwright downloads are self-contained.

To install only specific browsers (faster in CI if you don't need all three):

```bash
playwright install chromium
```

---

## 3. Locators: Choosing the Right One, in Order

Playwright locators are **lazy** — creating one (`page.locator(...)`, `page.get_by_role(...)`, etc.) does *not* query the DOM immediately. It just captures "how to find this element later." The actual lookup (and the auto-waiting described in [section 4](#4-auto-waiting-explained)) happens when you call an action or assertion on it. This is different from Selenium's `find_element()`, which queries the DOM immediately and hands back a reference to whatever matched *at that instant*.

Recommended priority order, and **why**:

1. **`get_by_role()`** — locates by ARIA role and accessible name, e.g. `page.get_by_role("button", name="Login")`. This is the top recommendation because it locates elements the way a real user (or a screen reader) perceives the page: by what it *is* and what it *says*, not by its CSS class or DOM position. A refactor that changes a `<button>`'s class name or nesting won't break this locator; a refactor that removes its accessible name is a real accessibility bug you'd want caught anyway. Using `get_by_role` in your tests is, as a side effect, a lightweight accessibility check on your app.
2. **`get_by_label()`** — for form fields, locates by their associated `<label>`. Reads like user intent ("the field labeled Password") and is immune to id/class churn.
3. **`get_by_text()`** — locates by visible text content. Good for links, buttons, headings, and one-off content that doesn't have a strong role/label story.
4. **`get_by_test_id()`** — locates by a dedicated test attribute (`data-testid` by default, configurable). This is a deliberate, stable contract between your app and your tests — the DOM can be restyled and restructured freely as long as the test id stays put. Reach for this when a role/label/text locator genuinely doesn't discriminate well, and when you (or your team) control the app's markup enough to add test ids.
5. **CSS locators** (`page.locator("#user-name")`, `.locator(".inventory_item")`, attribute selectors, etc.) — the fallback for markup that has no good semantics to hook into (common on pages you don't control, or older apps). This is what we use in this tutorial's `LoginPage` for saucedemo's login form fields and `InventoryPage` for its add-to-cart buttons, because those elements don't expose a role/label/test-id that uniquely identifies them.

**Why this ordering, concretely:**
- Accessibility-first locators (1–4) tend to survive UI refactors that only touch styling/structure, because they're anchored to *meaning*, not *implementation*.
- They read like a description of user behavior ("click the button named Login"), which makes tests self-documenting.
- They incidentally exercise your app's accessibility tree — a role/label locator that can't find your "Login" button might mean a real user with a screen reader can't find it either.
- CSS locators aren't wrong, they're just more brittle: a `.btn-primary` class or a `div > div:nth-child(3)` structural selector can break on a purely cosmetic change that a role/label locator would shrug off.

```python
# Preferred: role + accessible name
page.get_by_role("button", name="Add to cart").click()

# Preferred: label association
page.get_by_label("Password").fill("secret_sauce")

# Preferred: visible text
page.get_by_text("Checkout").click()

# Preferred: dedicated test id (data-testid by default)
page.get_by_test_id("checkout-button").click()

# Fallback: CSS, when there's no good semantic hook
page.locator("#user-name").fill("standard_user")
```

---

## 4. Auto-Waiting Explained

This is the single biggest day-to-day difference from Selenium, and it's worth understanding in depth.

### Actionability checks

Before Playwright performs an action like `.click()` or `.fill()`, it automatically runs a series of **actionability checks** on the target element and *retries them* until they all pass (or a timeout is hit):

- **Attached** — the element is in the DOM.
- **Visible** — it has a non-empty bounding box and no `visibility: hidden`/`display: none`.
- **Stable** — its bounding box hasn't changed over two consecutive animation frames (i.e. it's not mid-animation/transition).
- **Enabled** — it's not `disabled`.
- **Receives events** — it's not obscured by another element (e.g. a loading spinner or modal overlay sitting on top of it).

Only once all of these hold does Playwright actually dispatch the click/fill/etc. This is why Playwright test code has almost no explicit `wait_for_*` calls compared to Selenium: in Selenium, `element_to_be_clickable` (and friends) is something *you* wrap around actions yourself via `WebDriverWait`; in Playwright, an equivalent check is *baked into every action*, automatically, every time.

```python
# Playwright: the click() call itself waits for the button to be visible,
# stable, enabled, and unobscured before clicking. No separate wait needed.
page.get_by_role("button", name="Login").click()
```

### Web-first assertions: `expect()`

Auto-waiting on actions is only half the story. For *assertions*, Playwright provides **web-first assertions** via `expect()`:

```python
from playwright.sync_api import expect

expect(page.locator(".shopping_cart_badge")).to_be_visible()
expect(page.locator(".shopping_cart_badge")).to_have_text("1")
```

`expect(locator).to_be_visible()` doesn't just check the condition once — it **polls the live page, retrying the check, until it passes or a timeout elapses** (default 5s, configurable). This matters because a lot of test flakiness comes from checking a condition a single instant too early (e.g. right after a click, before a re-render finishes). A bare `assert` reads the DOM exactly once; `expect()` keeps checking. See [section 6](#6-assertions-why-expect-beats-a-bare-assert) for more.

### When you'd still reach for `page.wait_for_selector`

Auto-waiting covers the vast majority of cases, but there are times you want an *explicit* wait as a readability/intent signal or for something that isn't tied to a single action, e.g.:

```python
# Waiting for something to disappear before moving on, where there's no
# single action to hang the wait off of (e.g. a loading spinner clearing
# before you start a multi-step flow).
page.wait_for_selector(".loading-spinner", state="hidden")
```

Use it sparingly and deliberately — reach for `expect()` assertions and auto-waiting actions first; `wait_for_selector` is the exception, not the default, in Playwright (the opposite of Selenium, where explicit waits are the default).

---

## 5. Actions: click, fill, check, select_option, hover

All of these are `Locator` methods, and all of them auto-wait as described above before acting.

```python
# click — mouse click, waits for actionability first
page.get_by_role("button", name="Login").click()

# fill — clears the field and types the given text in one step
# (fires input events so JS-driven forms/validation see the change,
# unlike setting .value directly)
page.locator("#user-name").fill("standard_user")

# check — ticks a checkbox/radio; no-ops safely if already checked
page.get_by_label("Remember me").check()

# select_option — choose an <option> from a <select>, by value, label, or index
page.locator("#sort-dropdown").select_option(label="Price (low to high)")

# hover — moves the mouse over an element (e.g. to reveal a dropdown menu)
page.get_by_text("Menu").hover()
```

---

## 6. Assertions: Why `expect()` Beats a Bare `assert`

```python
from playwright.sync_api import expect

# Preferred: web-first assertion. Polls the badge's text until it equals
# "1" or the timeout elapses -- resilient to the small delay between a
# click and the UI re-rendering.
expect(cart_badge).to_have_text("1")

# Avoid: reads the DOM exactly once. If this line runs a few milliseconds
# before the badge updates, the test fails even though the app is working
# correctly -- classic source of flaky tests.
assert cart_badge.text_content() == "1"
```

The rule of thumb used throughout this tutorial's test files: **use `expect()` for anything you're asserting about the state of the page**, and reserve a bare `assert` for comparing two already-known Python values (e.g. a string you already retrieved and want to check against a second condition, or a computed value like a list length from data you already have in hand).

---

## 7. `playwright codegen`: Bootstrapping Locators

Playwright ships a code generator that records your interactions with a real browser and emits working Python locators/actions for you:

```bash
playwright codegen https://www.saucedemo.com
```

This opens a browser window alongside an "Inspector" window. As you click around, type into fields, etc., codegen writes out the corresponding Playwright calls in real time — and it automatically prefers the accessibility-based locators from [section 3](#3-locators-choosing-the-right-one-in-order) when the page's markup supports them.

**Use it for:**
- Quickly discovering what locator Playwright would pick for a given element (a great learning tool for the locator priority order).
- Bootstrapping the first draft of a new test or page object.

**Caveat — don't ship the raw output:** codegen produces one flat, linear script tied to a single recorded session. It has no Page Object Model structure, no fixtures, no reusable methods, and often no meaningful test assertions (just the actions you performed). Treat its output as a *starting point*: pull the locators it discovered into your page objects (like `LoginPage`/`InventoryPage` in this tutorial), delete the incidental noise, and add real `expect()` assertions before it becomes part of your actual suite.

---

## 8. The Trace Viewer for Debugging

A Playwright **trace** is a recorded timeline of a test run: every action, DOM snapshots before/after each step, console logs, network requests, and (optionally) a video — enough to fully reconstruct *what the browser was actually doing* without having watched it live.

Enable tracing via the `pytest-playwright` CLI flag (see also `pytest.ini` in this folder):

```bash
pytest --tracing=retain-on-failure
```

`retain-on-failure` records a trace for every test but only *keeps* the `trace.zip` file for tests that fail (passing tests' traces are discarded), which keeps disk usage sane while still capturing exactly the runs you need to debug. Traces are written under `test-results/`.

Open a saved trace with:

```bash
playwright show-trace test-results/<test-folder>/trace.zip
```

This opens an interactive viewer where you can:
- Scrub through a **timeline** of every action the test performed.
- Inspect a **DOM snapshot** at each step (exactly what the page looked like, clickable/inspectable like devtools).
- Read **console logs** and **network requests** captured during that step.
- See the **exact locator and actionability checks** Playwright ran before each action.

This is the closest thing Playwright has to Selenium's "add print statements and screenshots everywhere and re-run it" debugging loop — except you only need to run the failing test *once* to capture everything.

---

## 9. Built-in Fixtures: `page`, `context`, `browser`

`pytest-playwright` registers a set of pytest fixtures automatically, just by having the package installed — nothing to import or configure:

| Fixture | Scope | What it gives you |
|---|---|---|
| `browser` | session | A single launched Browser instance, shared and reused across the whole test session. |
| `context` | function | A brand-new, isolated `BrowserContext` for *this test only* — fresh cookies/storage, destroyed after the test. |
| `page` | function | A `Page` inside that fresh context, ready to use. Most tests only need this one. |

```python
def test_login(page: Page) -> None:
    page.goto("/")
    # ...
```

That's it — no `def page(): ... yield ... teardown` fixture to write yourself. **Contrast with Tutorial 2's Selenium `conftest.py`**, which had to hand-write a `driver` fixture: create the WebDriver, `yield` it, and explicitly call `driver.quit()` in teardown, getting cleanup right for every test and every browser. Because `pytest-playwright`'s `page`/`context` fixtures are already function-scoped and isolated per test, `conftest.py` in this tutorial (see below) has almost nothing to do beyond configuring `base_url`.

---

## 10. Page Object Model in Playwright

Same motivation as Selenium's Page Object Model (Tutorial 2): keep locators and low-level page interactions in one place per page, so tests read like business logic ("log in, then add an item to the cart") instead of a wall of raw selectors.

What's different in Playwright's version:

- **Locators are lazy**, so you can safely store them as instance attributes in `__init__` (as this tutorial's `LoginPage`/`InventoryPage` do) *before* the page has necessarily finished loading — nothing is queried until an action/assertion actually uses the locator.
- **Locators auto-wait**, so page object methods don't need their own explicit wait logic (see `base_page.py`'s docstring in this tutorial for exactly this point) — Selenium page objects often accumulate `WebDriverWait` boilerplate inside every method; Playwright page objects mostly don't need to.
- Page object methods should still return plain, useful values (strings, ints, other page objects) — the same discipline as Selenium's POM — so tests never reach around a page object to poke at `page.locator(...)` directly for things that page object already owns.

See `pages/base_page.py`, `pages/login_page.py`, and `pages/inventory_page.py` in this folder for the real implementations.

---

## 11. Project Structure

```
04-playwright-fundamentals/
├── README.md              <- you are here
├── requirements.txt        <- pytest, pytest-playwright, playwright
├── pytest.ini               <- default --browser, testpaths, documented CLI flags
├── conftest.py              <- base_url fixture override
├── pages/
│   ├── base_page.py         <- thin shared wrapper around Page
│   ├── login_page.py        <- LoginPage: goto(), login(), get_error_message()
│   └── inventory_page.py    <- InventoryPage: add_item_to_cart(), get_cart_count()
└── tests/
    ├── test_login.py        <- successful login, locked_out_user, wrong password
    └── test_cart.py         <- add-to-cart + cart badge assertions
```

---

## 12. Running the Tests

From inside `04-playwright-fundamentals/`:

```bash
# Install dependencies (once)
pip install -r requirements.txt
playwright install

# Run the whole suite, headless, verbose output
pytest -v

# Watch it run in a real browser window
pytest --headed

# Run with tracing enabled, keeping trace.zip only for failures
pytest --tracing=retain-on-failure

# Run a single test file
pytest tests/test_login.py -v

# Combine flags freely
pytest --headed --tracing=retain-on-failure -v
```

`pytest.ini` in this folder sets `--browser chromium` as the default and points `testpaths` at `tests/`, with the rest of the useful CLI flags documented as comments there.

---

## 13. Side-by-Side: Selenium vs Playwright

Same action — log in on saucedemo — in both frameworks:

```python
# --- Selenium (Tutorial 2 style) ---
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 10)
wait.until(EC.presence_of_element_located((By.ID, "user-name"))).send_keys("standard_user")
driver.find_element(By.ID, "password").send_keys("secret_sauce")
login_btn = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
login_btn.click()

error = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-test='error']")))
assert error.text == "Epic sadface: Sorry, this user has been locked out."
```

```python
# --- Playwright (this tutorial) ---
from playwright.sync_api import expect

page.locator("#user-name").fill("standard_user")
page.locator("#password").fill("secret_sauce")
page.locator("#login-button").click()

error = page.locator('[data-test="error"]')
expect(error).to_be_visible()
assert error.text_content() == "Epic sadface: Sorry, this user has been locked out."
```

Same outcome, but notice: no `WebDriverWait`, no `expected_conditions` imports, no explicit "wait until clickable" step — the `fill()`/`click()` calls handle that themselves, and `expect()` replaces the manual "wait until visible, then assert" two-step with one auto-retrying call.

---

## 14. What's Next

This tutorial covered the fundamentals: setup, locators, auto-waiting, actions, assertions, codegen, tracing, fixtures, and a first real Page Object Model suite.

Continue to **[Tutorial 5: Playwright Advanced & Production Patterns](../05-playwright-advanced-production-patterns/README.md)** for network interception/mocking, authentication state reuse across tests, parallel execution, visual comparisons, CI integration, and other patterns you'll need to run Playwright suites at production scale.
