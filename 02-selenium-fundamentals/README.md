# Tutorial 2: Selenium WebDriver Fundamentals — Locators, Waits & Your First Test Suite

> Part of the **Selenium & Playwright Test Automation Tutorials** series.
> Previous: [Tutorial 1 — Foundations & Environment Setup](../01-foundations-and-environment-setup/README.md)
> Next: [Tutorial 3 — Selenium Advanced / Production Patterns](../03-selenium-advanced-production-patterns/README.md)

In Tutorial 1 you installed Selenium, wired up `webdriver-manager`, and
launched a browser for a "Hello World" check. In this tutorial you'll build
a **real, runnable, Page-Object-Model test suite** against a live demo
application — [saucedemo.com](https://www.saucedemo.com/), a standard
e-commerce site built specifically for test automation practice.

By the end, you'll have a small but genuinely production-shaped project:
page objects, a `conftest.py` with fixtures and a failure-screenshot hook,
and pytest tests that log in, handle failures, and add items to a cart.

## About the app under test

[saucedemo.com](https://www.saucedemo.com/) is a fake e-commerce store
maintained for exactly this purpose — learning and practicing test
automation. It ships with several seeded accounts; the two we'll use here:

| Username | Password | Behavior |
|---|---|---|
| `standard_user` | `secret_sauce` | Logs in normally |
| `locked_out_user` | `secret_sauce` | Login succeeds server-side but the UI blocks the user with an error — great for testing failure paths |

## Table of contents

1. [Project structure](#1-project-structure)
2. [WebDriver basics: the driver lifecycle](#2-webdriver-basics-the-driver-lifecycle)
3. [Browser options: headless mode & window size](#3-browser-options-headless-mode--window-size)
4. [Locator strategies](#4-locator-strategies)
5. [`find_element` vs `find_elements`](#5-find_element-vs-find_elements)
6. [Interacting with elements](#6-interacting-with-elements)
7. [Waits: why explicit beats implicit (and never mix them)](#7-waits-why-explicit-beats-implicit-and-never-mix-them)
8. [Assertions with pytest](#8-assertions-with-pytest)
9. [The Page Object Model (POM)](#9-the-page-object-model-pom)
10. [pytest fixtures: `conftest.py` and failure screenshots](#10-pytest-fixtures-conftestpy-and-failure-screenshots)
11. [Running the suite](#11-running-the-suite)
12. [What's next](#12-whats-next)

---

## 1. Project structure

```
02-selenium-fundamentals/
├── README.md                 # this file
├── requirements.txt          # selenium, webdriver-manager, pytest, pytest-html
├── pytest.ini                # pytest configuration (test paths, markers)
├── conftest.py                # `driver` fixture + failure-screenshot hook
├── pages/
│   ├── base_page.py           # shared WebDriverWait-based actions
│   ├── login_page.py          # page object for the login screen
│   └── inventory_page.py      # page object for the post-login products page
├── tests/
│   ├── test_login.py          # login: success, locked-out user, wrong password
│   └── test_cart.py           # add-to-cart and cart badge count
└── screenshots/                # created automatically on test failure
```

Install dependencies (inside the venv you created in Tutorial 1):

```bash
pip install -r requirements.txt
```

---

## 2. WebDriver basics: the driver lifecycle

Every Selenium test follows the same three-phase lifecycle:

1. **Create** a driver — this launches an actual, real browser process.
2. **Use** it — navigate, find elements, interact, assert.
3. **Quit** it — `driver.quit()` closes the browser *and* ends the
   WebDriver session/process. This is not optional: skipping it leaks
   browser processes that pile up across a test run (or a CI pipeline)
   until the machine runs out of memory.

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

try:
    driver.get("https://www.saucedemo.com/")
    print(driver.title)
finally:
    driver.quit()  # always runs, even if something above raises
```

Note `driver.quit()` vs `driver.close()`: `close()` closes the current
*window/tab* and leaves the browser session alive if other windows are
open; `quit()` closes every window and ends the whole session. In tests,
you almost always want `quit()`.

In this tutorial's suite, you never write this boilerplate directly — the
`driver` fixture in [`conftest.py`](conftest.py) handles create/yield/quit
for every test automatically. See [§10](#10-pytest-fixtures-conftestpy-and-failure-screenshots).

---

## 3. Browser options: headless mode & window size

`Options` configure *how* the browser launches, before it launches:

```python
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--start-maximized")   # avoid a small default viewport
options.add_argument("--headless=new")      # no visible window
options.add_argument("--window-size=1920,1080")
```

**Why headless matters for CI:** CI runners typically have no display
server at all — a normal (headed) browser launch fails outright on most CI
images. Headless Chrome renders the page and runs the DOM/JS engine
exactly as usual, just without drawing pixels to a screen, which makes it:

- **Required** on headless CI runners (no display to draw to).
- **Faster and lighter** — no compositing/painting work, which matters
  when you're running many tests in parallel on shared infrastructure.

Locally, running *headed* (a visible window) is genuinely useful while
you're learning or debugging — watching the browser click through your
test is one of the fastest ways to understand what Selenium is doing, and
to spot *why* a locator isn't matching.

This project supports both via a custom `--headless` pytest flag (defined
in `conftest.py` with `pytest_addoption` — see [§10](#10-pytest-fixtures-conftestpy-and-failure-screenshots)):

```bash
pytest -v                # headed — watch the browser
pytest -v --headless     # headless — what CI will run
```

One more note on window size: a small or default viewport is a common,
sneaky cause of flaky tests — elements that exist but render off-screen or
behind a responsive "hamburger" menu can fail to be clickable. Always set
an explicit size (headless) or maximize (headed) rather than relying on
Selenium's default window.

---

## 4. Locator strategies

A **locator** tells Selenium *which element* you mean. Selenium supports
several strategies via `selenium.webdriver.common.by.By`:

| Strategy | `By` constant | Example | Use when |
|---|---|---|---|
| ID | `By.ID` | `"user-name"` | The element has a stable, unique `id` — fastest and most robust option |
| CSS selector | `By.CSS_SELECTOR` | `"#login-button"` | Almost everything else — preferred default |
| Name | `By.NAME` | `"user-name"` | Common on form inputs; a reasonable fallback when there's no `id` |
| Class name | `By.CLASS_NAME` | `"inventory_item"` | A single, specific class — beware classes shared by many elements |
| XPath | `By.XPATH` | `"//div[text()='Sauce Labs Backpack']"` | Only when you need to match by **text** or traverse **up** the DOM |

All examples below are real, working locators against saucedemo.com's
actual login page DOM:

```html
<input class="form_input" id="user-name" name="user-name" ... />
<input class="form_input" id="password" name="password" type="password" ... />
<input type="submit" class="submit-button btn_action" id="login-button" ... />
```

```python
from selenium.webdriver.common.by import By

# By ID — the element's `id` attribute is unique and stable
(By.ID, "user-name")

# By CSS selector — same element, ID-selector syntax
(By.CSS_SELECTOR, "#user-name")

# By name — falls back to the `name` attribute
(By.NAME, "user-name")

# By class name — matches the input's `form_input` class
# (fragile here since MULTIPLE inputs share this class — shown for
# illustration, not recommended for this particular element)
(By.CLASS_NAME, "form_input")

# By XPath — matching the submit button by its id, XPath-style
(By.XPATH, "//input[@id='login-button']")
```

### Prefer CSS selectors over XPath

**Guidance: reach for a CSS selector by default. Reserve XPath for the two
things CSS genuinely cannot do — matching by visible text, and traversing
*upward* from a child to a parent/ancestor.**

Why CSS first:

- **Faster.** Browsers implement native, highly-optimized CSS selector
  engines (the same one used for stylesheets); XPath evaluation goes
  through a separate, generally slower engine.
- **More readable.** `.inventory_item_price` reads at a glance; the XPath
  equivalent (`//div[@class='inventory_item_price']`) is more to parse for
  no added benefit.
- **Less brittle to attribute reordering** and generally the convention
  the wider web dev / QA community already knows from CSS itself.

When XPath *is* the right tool — this suite uses exactly this case in
[`pages/inventory_page.py`](pages/inventory_page.py) to find an
"Add to cart" button by the product's visible name and then walk **up** to
its containing card:

```python
# CSS cannot select by text content or move upward in the tree — XPath can.
name_locator = (By.XPATH, f"//div[@class='inventory_item_name' and text()='{item_name}']")
name_element = driver.find_element(*name_locator)

# Walk UP from the matched text node to its ancestor card, then back DOWN
# to that card's button — impossible to express purely in CSS.
button = name_element.find_element(By.XPATH, "./ancestor::div[@class='inventory_item']//button")
```

### `NoSuchElementException`

If a locator matches nothing, `find_element` raises
`selenium.common.exceptions.NoSuchElementException` immediately — it does
**not** wait or retry on its own. This is exactly why we don't call
`find_element` directly in tests/page objects; see [§7](#7-waits-why-explicit-beats-implicit-and-never-mix-them)
on why we wrap every lookup in an explicit `WebDriverWait` instead, which
gives the page time to render before deciding the element truly isn't there.

```python
from selenium.common.exceptions import NoSuchElementException

try:
    driver.find_element(By.ID, "does-not-exist")
except NoSuchElementException:
    print("Element genuinely isn't in the DOM (not just 'not yet').")
```

---

## 5. `find_element` vs `find_elements`

- **`find_element(by, value)`** returns the **first** matching element, or
  raises `NoSuchElementException` if there are zero matches.
- **`find_elements(by, value)`** (plural) returns a **list** of every
  matching element — an **empty list**, not an exception, if there are no
  matches. This makes `find_elements` the right tool whenever "zero" is a
  valid, expected outcome (e.g. checking whether an error banner is
  present, or counting product cards):

```python
# Checking existence WITHOUT risking an exception:
error_elements = driver.find_elements(By.CSS_SELECTOR, '[data-test="error"]')
if error_elements:
    print("An error is showing:", error_elements[0].text)

# Counting all product cards on the inventory page:
items = driver.find_elements(By.CSS_SELECTOR, ".inventory_item")
print(f"{len(items)} products found")
```

`InventoryPage.get_inventory_item_count()` in this suite is a direct
example of `find_elements` used for counting.

---

## 6. Interacting with elements

Once you have a `WebElement`, the common interactions are:

```python
element = driver.find_element(By.ID, "user-name")

element.click()                 # mouse click
element.send_keys("standard_user")  # type text (appends to existing content!)
element.clear()                 # clear a text input/textarea before typing
text = element.text             # read the element's rendered, visible text
is_shown = element.is_displayed()
is_on = element.is_selected()   # checkboxes/radio buttons
```

**`send_keys` appends — it does not replace.** Always `clear()` first if
the field might already contain text (this is exactly what
`BasePage.type_text()` does for you automatically in this project).

### Checkboxes

```python
checkbox = driver.find_element(By.ID, "some-checkbox")
if not checkbox.is_selected():
    checkbox.click()   # toggling is just a click; there's no "check()" method
```

### `<select>` dropdowns — the `Select` class

Selenium provides a dedicated `Select` wrapper for HTML `<select>`
elements — never `.click()` a `<select>` and try to click an `<option>`
manually; use `Select` instead:

```python
from selenium.webdriver.support.ui import Select

sort_dropdown = driver.find_element(By.CSS_SELECTOR, ".product_sort_container")
select = Select(sort_dropdown)

select.select_by_visible_text("Price (low to high)")
# or:
select.select_by_value("lohi")
# or:
select.select_by_index(1)

current = select.first_selected_option.text
```

(saucedemo's inventory page has exactly this dropdown — `.product_sort_container`
— for sorting products; a great one to practice `Select` against once
you're logged in.)

---

## 7. Waits: why explicit beats implicit (and never mix them)

Web pages render asynchronously — JavaScript fetches data, animations run,
elements appear after a delay. A test that interacts with an element the
instant `driver.get()` returns will frequently fail, not because the
feature is broken, but because the page simply hadn't finished rendering
yet. Waits solve this.

### Implicit waits

```python
driver.implicitly_wait(10)  # applies globally, to every find_element(s) call
```

An implicit wait tells the driver: "for *any* element lookup, if it's not
immediately found, keep polling for up to N seconds before giving up."
It's set once and silently applies everywhere for the life of the driver.

### Explicit waits (recommended)

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 10)
element = wait.until(EC.visibility_of_element_located((By.ID, "user-name")))
```

An explicit wait waits for a **specific condition**, on a **specific
element**, at a **specific point in the test** — and nowhere else.

### Why mixing them is dangerous

Selenium's own documentation warns against combining implicit and
explicit waits in the same driver session, and for good reason: the two
timeouts can **stack unpredictably**. A `WebDriverWait.until(...)` call
internally polls via repeated `find_element` calls — if an implicit wait
is *also* active, each of those internal polls can itself wait up to the
implicit timeout before returning "not found," inflating an intended
10-second explicit wait into something far longer and far less
predictable. The result is a suite that's both **slower** (worst-case
timeouts compound) and **flakier** (failure timing becomes inconsistent
and hard to reason about).

**The production-recommended approach: use explicit waits exclusively.**
Never call `driver.implicitly_wait(...)` in this codebase. Every wait in
this suite goes through `BasePage`'s `WebDriverWait`-backed helpers
(`wait_visible`, `wait_clickable`), so every page object and test
automatically gets this behavior for free — see [`pages/base_page.py`](pages/base_page.py).

### The `expected_conditions` (`EC`) you'll use most

```python
from selenium.webdriver.support import expected_conditions as EC

# Element exists AND is visible (not display:none, not zero-size) —
# the right condition before reading text or asserting presence.
wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".inventory_item")))

# Element is visible AND enabled — the right condition immediately
# before a .click().
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#login-button")))
```

Using `visibility_of_element_located` before a click (instead of
`element_to_be_clickable`) is a common source of "element not
interactable" errors — the element can be visible while still disabled.
Match the wait condition to what you're about to *do*.

Also **never use a hardcoded `time.sleep(...)`** to "wait for the page."
A sleep either wastes time waiting longer than necessary, or — worse —
doesn't wait long enough under load and fails intermittently anyway. This
project has no `time.sleep` calls anywhere; every wait is an explicit,
condition-based `WebDriverWait`.

---

## 8. Assertions with pytest

pytest lets you use Python's plain built-in `assert` — no special
`self.assertEqual(...)` API required:

```python
assert driver.current_url.endswith("/inventory.html")
assert login_page.get_error_message() == "Epic sadface: Sorry, this user has been locked out."
```

This works well *because* of pytest's **assertion rewriting**: pytest
inspects the `assert` statement at collection time and, on failure, prints
a detailed breakdown of both sides of the comparison (e.g. a full string
diff), not just `AssertionError`. You get equivalent (often better)
failure output to a dedicated assertion library, with plain Python syntax.

See `tests/test_login.py` and `tests/test_cart.py` for real examples —
every assertion in this suite is a plain `assert`.

---

## 9. The Page Object Model (POM)

The **Page Object Model** is the standard structural pattern for UI test
suites: **one class per page (or logical component) of the app**, which
owns that page's locators and the actions you can perform on it. Tests
call methods on page objects; they never touch `driver.find_element(...)`
or a raw locator directly.

### Why it exists

- **Separation of concerns.** Locators and low-level Selenium calls live
  in page objects; test files stay focused on *test logic* — the
  business rules being verified — and read like plain English.
- **Eliminates duplication.** Without POM, "type into the username field"
  ends up copy-pasted (with slightly different waits/locators) into every
  test that needs to log in. With POM, it's one method, `login()`, called
  everywhere.
- **Centralizes maintenance.** When the UI changes — an `id` gets
  renamed, a button moves — you fix it in **one place** (the page
  object), and every test that depends on it is automatically fixed too.
  Without POM, you'd hunt down every test file that duplicated that
  locator.

### This project's structure

```
pages/
├── base_page.py       # BasePage — shared WebDriverWait actions (click, type_text, ...)
├── login_page.py       # LoginPage(BasePage) — open(), login(), get_error_message()
└── inventory_page.py   # InventoryPage(BasePage) — add_item_to_cart(), get_cart_count()
```

- **`BasePage`** ([`pages/base_page.py`](pages/base_page.py)) holds every
  page object's shared plumbing: `click`, `type_text`, `get_text`,
  `wait_visible`, `wait_clickable`, `is_visible`. Every concrete page
  object inherits from it, so wait/interaction logic is written exactly
  once for the whole suite.
- **`LoginPage`** ([`pages/login_page.py`](pages/login_page.py)) owns the
  login form's locators and exposes `open()`, `login(username, password)`,
  and `get_error_message()`.
- **`InventoryPage`** ([`pages/inventory_page.py`](pages/inventory_page.py))
  owns the products page's locators and exposes `add_item_to_cart(item_name)`
  and `get_cart_count()`.

A test, by contrast, reads like this — no locators, no waits, just intent:

```python
def test_successful_login_redirects_to_inventory_page(driver):
    login_page = LoginPage(driver)
    login_page.open()
    login_page.login("standard_user", "secret_sauce")

    assert "/inventory.html" in driver.current_url
```

---

## 10. pytest fixtures: `conftest.py` and failure screenshots

`conftest.py` is a special pytest filename: fixtures and hooks defined
there are automatically available to every test file in the same
directory (and subdirectories) — no import needed. This project's
[`conftest.py`](conftest.py) provides two things:

### The `driver` fixture

```python
@pytest.fixture(scope="function")
def driver(request):
    ...
    yield chrome_driver
    chrome_driver.quit()
```

Any test that declares a `driver` parameter (e.g. `def test_x(driver):`)
gets a **fresh, ready-to-use** Chrome WebDriver — pytest handles calling
the fixture, injecting its return value, and running the teardown code
after `yield` once the test finishes, pass or fail. `scope="function"`
(the default) means a **new browser per test**, which trades a bit of
speed for full test isolation — no test can leak cookies, open tabs, or
navigation state into another.

The fixture also reads a custom `--headless` CLI flag, registered via
`pytest_addoption` (another special `conftest.py` hook), so the same test
code runs headed locally and headless in CI without any changes to the
tests themselves — see [§3](#3-browser-options-headless-mode--window-size).

### Automatic screenshot-on-failure

```python
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    web_driver = item.funcargs.get("driver")
    ...
    web_driver.save_screenshot(screenshot_path)
```

`pytest_runtest_makereport` is a pytest hook that runs after each phase
(setup/call/teardown) of every test and produces that phase's report. By
wrapping it (`hookwrapper=True`) and checking `report.when == "call"` and
`report.failed`, we run code **only when the actual test body failed** —
not on setup errors or successful teardown. `item.funcargs` holds the
resolved fixture values for that test, so `item.funcargs.get("driver")`
retrieves the *same browser instance* the failing test was using,
letting us capture a screenshot of the exact failure state before the
`driver` fixture's teardown closes it. Screenshots land in `screenshots/`,
named after the test and timestamped.

This is a genuinely production-grade pattern: when a CI run fails at 2 AM,
a screenshot of what the browser actually saw is often the fastest path
to understanding why.

---

## 11. Running the suite

```bash
# Run everything, verbose output, headed (visible browser)
pytest -v

# Run headless — what CI should run
pytest -v --headless

# Generate a self-contained HTML report (open report.html in a browser)
pytest --html=report.html --self-contained-html

# Run just one file, or one test
pytest tests/test_login.py -v
pytest tests/test_login.py::test_successful_login_redirects_to_inventory_page -v

# Run only tests marked @pytest.mark.smoke (see pytest.ini)
pytest -m smoke -v
```

If a test fails, check the `screenshots/` folder for a snapshot of the
browser at the moment of failure, and check `report.html` (if generated)
for a shareable summary.

---

## 12. What's next

- **[Tutorial 3 — Selenium Advanced / Production Patterns](../03-selenium-advanced-production-patterns/README.md)**
  builds on this project's `pages/` and `tests/` structure with topics
  like handling iframes and multiple windows/tabs, custom expected
  conditions, retry/rerun strategies, parallel execution, and CI
  integration.
- **[Tutorial 4 — Playwright Fundamentals](../04-playwright-fundamentals/README.md)**
  implements this *exact same* saucedemo login/cart test suite again, but
  in Playwright — a deliberate side-by-side so you can directly compare
  how the two frameworks approach locators, waiting, and the Page Object
  Model.
