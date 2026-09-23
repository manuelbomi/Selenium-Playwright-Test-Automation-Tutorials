# Tutorial 3 — Advanced Selenium: Page Object Model at Scale, Parallel Execution & CI/CD

Part 3 of the **Selenium & Playwright Test Automation Tutorials** series.

> **Prerequisite:** [Tutorial 2 — Selenium Fundamentals](../02-selenium-fundamentals/README.md)
> got you a *working* test suite against [saucedemo.com](https://www.saucedemo.com/): WebDriver
> lifecycle, locators, explicit waits, and a basic Page Object Model
> (`pages/base_page.py`, `pages/login_page.py`, `pages/inventory_page.py`, a
> `driver` fixture in `conftest.py`). This tutorial is self-contained — every
> file it needs is in this folder — but it assumes you're comfortable with
> those basics and picks up exactly where Tutorial 2 left off: turning "a
> working test suite" into a **production-grade automation framework**.

By the end of this tutorial you will have a suite that:

- Composes page objects out of small, reusable components instead of one
  giant class per page
- Handles the four browser widgets that trip up most Selenium beginners:
  iframes, native JS dialogs, multiple windows/tabs, and file uploads
- Runs against Chrome, Firefox, or Edge from the same test code
- Reads all configuration (URLs, browser choice, credentials) from
  environment variables — never hardcoded
- Runs in parallel with `pytest-xdist`
- Runs against a Dockerized Selenium Grid instead of local browser binaries
- Automatically retries genuinely flaky (environment-caused) failures
- Captures a screenshot, the page source, and browser console logs the
  moment any test fails
- Runs headlessly in GitHub Actions on every push/PR, with the HTML report
  and failure artifacts attached to the build

---

## Table of Contents

1. [Project Layout](#1-project-layout)
2. [Setup](#2-setup)
3. [Scaling the Page Object Model](#3-scaling-the-page-object-model)
4. [Handling Browser Widgets](#4-handling-browser-widgets-iframes-alerts-windows-uploads)
5. [Cross-Browser Testing: the Browser Factory](#5-cross-browser-testing-the-browser-factory)
6. [Config Management: Never Hardcode Secrets](#6-config-management-never-hardcode-secrets)
7. [Parallel Execution with pytest-xdist](#7-parallel-execution-with-pytest-xdist)
8. [Selenium Grid with Docker](#8-selenium-grid-with-docker)
9. [Retry Logic for Flaky Tests](#9-retry-logic-for-flaky-tests)
10. [Failure Diagnostics](#10-failure-diagnostics-screenshots-page-source-console-logs)
11. [CI/CD with GitHub Actions](#11-cicd-with-github-actions)
12. [Production Best Practices Checklist](#12-production-best-practices-checklist)
13. [What's Next](#13-whats-next)

---

## 1. Project Layout

```
03-selenium-advanced-production-patterns/
├── README.md                       # this file
├── requirements.txt                 # pinned dependency ranges
├── .env.example                     # documented config template — commit this
├── .gitignore                       # keeps .env, artifacts/, report.html out of git
├── pytest.ini                       # pytest config (pythonpath, markers, addopts)
├── config.py                        # THE single place that reads env vars
├── conftest.py                      # browser factory, `driver` fixture, failure hook
├── docker-compose.yml               # local Selenium Grid (hub + Chrome + Firefox nodes)
├── pages/
│   ├── __init__.py
│   └── base_page.py                 # shared waits + iframe/alert/window/upload helpers
├── tests/
│   ├── __init__.py
│   ├── test_widgets.py              # iframe, alert, window, upload examples
│   └── fixtures/
│       └── sample_upload.txt        # dummy file used by the upload test
└── .github/
    └── workflows/
        └── selenium-ci.yml          # headless, parallel CI run + artifact upload
```

## 2. Setup

```bash
cd 03-selenium-advanced-production-patterns
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env             # then edit .env if you need non-default values
```

Run the default suite (Chrome, local, sequential):

```bash
pytest
```

Run headless, in Firefox, with an HTML report:

```bash
pytest --browser=firefox --headless --html=report.html --self-contained-html
```

---

## 3. Scaling the Page Object Model

Tutorial 2's Page Object Model works fine for a handful of pages. It stops
working once a real application has 30+ pages sharing headers, nav bars,
modals, and toast notifications. Two patterns fix that.

### 3.1 A `BasePage` with common waits

Every page object should inherit shared, **generic** behavior — never
sleep-based, always explicit-wait-based — instead of re-implementing
`WebDriverWait(...).until(...)` in every page class. See
[`pages/base_page.py`](pages/base_page.py):

```python
class BasePage:
    def __init__(self, driver, timeout=None):
        self.driver = driver
        self.timeout = timeout or config.explicit_wait
        self.wait = WebDriverWait(self.driver, self.timeout)

    def find(self, locator):
        return self.wait.until(EC.presence_of_element_located(locator))

    def click(self, locator):
        self.find_clickable(locator).click()
    # ...
```

Page objects then extend it with **only** their own locators and workflows:

```python
class LoginPage(BasePage):
    USERNAME_INPUT = (By.ID, "user-name")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-button")

    def login(self, username: str, password: str) -> None:
        self.type_text(self.USERNAME_INPUT, username)
        self.type_text(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)
```

### 3.2 Avoiding the "God object" page class

The failure mode at scale isn't *too few* page objects — it's **one page
object that knows everything about a page**: 40 locators, checkout logic,
cart logic, header/nav logic, and toast-message assertions, all in a single
1,000-line `InventoryPage` class. Symptoms: every unrelated feature change
touches the same file, merge conflicts pile up, and the class becomes
untestable in isolation.

**Fix: compose complex pages out of smaller component objects.** A
component object models one reusable *piece of UI* (a header, a nav
sidebar, a cart widget, a modal) that shows up on multiple pages, and a
page object owns only the parts of the page that are actually unique to it
plus instances of the components it contains:

```python
class HeaderComponent(BasePage):
    """The top nav bar — present on every authenticated saucedemo page."""
    CART_BADGE = (By.CSS_SELECTOR, ".shopping_cart_badge")
    MENU_BUTTON = (By.ID, "react-burger-menu-btn")
    LOGOUT_LINK = (By.ID, "logout_sidebar_link")

    def cart_count(self) -> int:
        try:
            return int(self.get_text(self.CART_BADGE))
        except TimeoutException:
            return 0  # badge doesn't render at all when the cart is empty

    def logout(self) -> None:
        self.click(self.MENU_BUTTON)
        self.click(self.LOGOUT_LINK)


class InventoryPage(BasePage):
    """Owns ONLY inventory-specific locators/behavior; delegates the rest."""
    ADD_TO_CART_BUTTONS = (By.CSS_SELECTOR, "button.btn_inventory")

    def __init__(self, driver):
        super().__init__(driver)
        self.header = HeaderComponent(driver)   # composition, not inheritance

    def add_first_item_to_cart(self) -> None:
        self.find_all(self.ADD_TO_CART_BUTTONS)[0].click()
```

A test then reads as a story instead of a locator dump:

```python
def test_cart_badge_increments(driver):
    inventory = InventoryPage(driver)
    inventory.add_first_item_to_cart()
    assert inventory.header.cart_count() == 1
```

Rules of thumb:

- If two or more pages share a chunk of UI, it's a **component**, not
  copy-pasted locators.
- A page object should be composed *of* components (`self.header = ...`),
  never inherit from a component just to reuse its locators.
- `BasePage` stays app-agnostic forever. The moment it references a
  saucedemo-specific ID, that logic has leaked in from the wrong layer.

---

## 4. Handling Browser Widgets (iframes, alerts, windows, uploads)

saucedemo.com is a clean SPA with no iframes, native dialogs, popups, or
file inputs — great for Tutorial 2, useless for teaching these mechanics.
This tutorial instead targets
**[the-internet.herokuapp.com](https://the-internet.herokuapp.com/)**, a
public demo app purpose-built with a page per widget. All four examples
live in [`tests/test_widgets.py`](tests/test_widgets.py), built on helper
methods added to [`pages/base_page.py`](pages/base_page.py).

### 4.1 Iframes — [`/iframe`](https://the-internet.herokuapp.com/iframe)

An iframe embeds an entirely separate HTML document. Selenium only "sees"
whichever document the driver is currently focused on — elements inside an
iframe are invisible to `find_element` until you explicitly switch into it,
and everything outside the iframe becomes invisible until you switch back.

```python
page.switch_to_iframe((By.ID, "mce_0_ifr"))   # switch INTO the iframe
editable_body = page.find((By.ID, "tinymce"))
editable_body.send_keys("Hello from an automated test!")

page.switch_to_default_content()               # switch back to the top-level page
```

Under the hood, `switch_to_iframe` uses
`EC.frame_to_be_available_and_switch_to_it(locator)` — an explicit wait
that also switches context, rather than a bare `driver.switch_to.frame(...)`
which would race the iframe's own load.

### 4.2 JS Alerts / Confirms / Prompts — [`/javascript_alerts`](https://the-internet.herokuapp.com/javascript_alerts)

Native browser dialogs (`window.alert`, `window.confirm`, `window.prompt`)
are **not** part of the page DOM — you cannot `find_element` your way into
one. Selenium exposes them through `driver.switch_to.alert`:

```python
page.click((By.CSS_SELECTOR, "button[onclick='jsAlert()']"))
alert_text = page.accept_alert()     # switch_to.alert -> .accept()

page.click((By.CSS_SELECTOR, "button[onclick='jsConfirm()']"))
page.dismiss_alert()                 # switch_to.alert -> .dismiss() (Cancel)

page.click((By.CSS_SELECTOR, "button[onclick='jsPrompt()']"))
page.accept_prompt("automation")     # .send_keys(text) then .accept()
```

Always wait for the alert with `EC.alert_is_present()` before touching it
(`wait_for_alert()` does this) — clicking a button that triggers a dialog
and immediately calling `driver.switch_to.alert` is a race condition.

### 4.3 Multiple Windows / Tabs — [`/windows`](https://the-internet.herokuapp.com/windows)

Clicking a `target="_blank"` link opens a new tab, but the driver's focus
**stays on the original tab** until you explicitly switch:

```python
original_handle = driver.current_window_handle
original_handles = driver.window_handles   # capture BEFORE the click

page.click((By.LINK_TEXT, "Click Here"))
page.switch_to_new_window(original_handles)  # waits for handle count to grow

assert driver.title == "New Window"

page.close_and_switch_back(original_handle)  # close extra tab, refocus original
```

Capturing `window_handles` *before* the action that opens the new window is
what makes it possible to reliably compute *which* handle is new — `set(new) -
set(old)`. Always close extra windows/tabs you open in a test; leaked
windows are a common source of state bleeding into the next test.

### 4.4 File Upload — [`/upload`](https://the-internet.herokuapp.com/upload)

Selenium cannot drive OS-native file picker dialogs — there's no DOM to
interact with once one opens. The trick is that you never need to open one:
a `<input type="file">` element accepts a file path directly via
`send_keys()`:

```python
page.upload_file((By.ID, "file-upload"), "/absolute/path/to/sample_upload.txt")
page.click((By.ID, "file-submit"))

assert page.get_text((By.ID, "uploaded-files")) == "sample_upload.txt"
```

This works identically headless or headed, because no OS dialog is ever
involved — see [`tests/fixtures/sample_upload.txt`](tests/fixtures/sample_upload.txt),
a small dummy file checked into the repo for exactly this purpose.

**File upload against Grid:** the path you pass must exist on the machine
running the *browser*, not necessarily the machine running the *test
process*. For a local driver these are the same machine. Selenium 4's
`Remote` driver enables `LocalFileDetector` by default, which transparently
zips and transfers the local file to the remote node before typing in the
path — so the example above works unmodified against
[the Grid setup in §8](#8-selenium-grid-with-docker) with no extra volume
mounts. If you ever explicitly disable `LocalFileDetector` for performance
reasons, you'd need to mount the file into the node container yourself.

---

## 5. Cross-Browser Testing: the Browser Factory

Real bugs hide in browser differences — a CSS flexbox quirk in Safari, a
date-picker rendering issue in Firefox. Supporting multiple browsers should
be a **config change**, not a fork of your test suite. That's the job of
the browser factory in [`conftest.py`](conftest.py):

```python
def build_driver(browser: str, headless: bool, grid_url: str = ""):
    """The single place that knows how to construct a WebDriver."""
    options = _OPTION_BUILDERS[browser.lower()](headless)

    if grid_url:
        return webdriver.Remote(command_executor=grid_url, options=options)

    if browser == "chrome":
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    if browser == "firefox":
        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)
    # edge...
```

[`webdriver-manager`](https://pypi.org/project/webdriver-manager/) downloads
and caches the correct driver binary version for whatever browser is
actually installed, so nobody manually tracks chromedriver / geckodriver /
msedgedriver versions — a classic source of "works on my machine" CI
failures.

Run the exact same test suite against three browsers:

```bash
pytest --browser=chrome
pytest --browser=firefox
pytest --browser=edge
```

Because no test or page object ever imports `webdriver.Chrome` directly —
they only ever receive an already-built `driver` fixture — none of them
need to know or care which browser is actually running.

---

## 6. Config Management: Never Hardcode Secrets

**Never hardcode secrets, credentials, or environment-specific URLs in test
code.** Not "as a shortcut for now," not "just for this demo app" — always,
even when (as with saucedemo's `standard_user` / `secret_sauce`) the
credential itself is public. The pattern is what matters: it's the same
pattern that keeps a *real* password out of your git history.

[`config.py`](config.py) is the **only** module in this project allowed to
call `os.getenv`. Everything else — `conftest.py`, page objects, tests —
imports the resolved `config` object:

```python
from dotenv import load_dotenv
load_dotenv()   # loads .env if present; never overrides real env vars already set

@dataclass(frozen=True)
class Config:
    base_url: str = os.getenv("BASE_URL", "https://www.saucedemo.com")
    browser: str = os.getenv("BROWSER", "chrome").lower()
    sauce_username: str = os.getenv("SAUCE_USERNAME", "standard_user")
    sauce_password: str = os.getenv("SAUCE_PASSWORD", "secret_sauce")
    selenium_grid_url: str = os.getenv("SELENIUM_GRID_URL", "")
    # ...

config = Config()
```

```python
# ✅ correct — reads through config.py
login_page.login(config.sauce_username, config.sauce_password)

# ❌ never do this — a credential baked directly into test code
login_page.login("standard_user", "secret_sauce")
```

**`.env` vs. `.env.example`:**

| File            | Committed? | Contains                                      |
|------------------|:---------:|------------------------------------------------|
| `.env.example`   | ✅ yes     | Placeholder/demo values + comments, the template |
| `.env`           | ❌ never   | Your real local values — listed in `.gitignore` |

In CI, real secrets are injected as actual environment variables (GitHub
Actions Secrets — see [§11](#11-cicd-with-github-actions)), which always
win over anything in a `.env` file, because `load_dotenv()` refuses to
override variables that already exist in the process environment.

---

## 7. Parallel Execution with pytest-xdist

```bash
pip install pytest-xdist   # already in requirements.txt
pytest -n auto             # -n auto: one worker per CPU core
pytest -n 4                # or pin an explicit worker count
```

`pytest-xdist` splits the test suite across worker **processes** and runs
them concurrently. This is where the function-scoped `driver` fixture in
`conftest.py` stops being a style preference and becomes a correctness
requirement:

- **Isolation across workers:** each `xdist` worker is a separate process
  with its own Python interpreter — fixtures are never literally shared
  across workers, so that part is safe by construction.
- **Isolation across tests within a worker:** a single worker still runs
  many tests sequentially, one after another. If the `driver` fixture were
  `session`- or `module`-scoped, tests *within the same worker* would
  share one browser instance — leaking cookies, localStorage, open alerts,
  and extra windows from one test into the next, and making test order
  matter (breaking idempotency).

```python
@pytest.fixture           # function-scoped by default — do not widen this
def driver(request):
    drv = build_driver(...)
    yield drv
    drv.quit()
```

The cost is real — a fresh browser per test is slower than reusing one —
but it's the only way parallel runs stay deterministic. You get the speed
back from parallelism itself, and from Grid providing enough real browser
capacity to run many sessions at once (next section).

---

## 8. Selenium Grid with Docker

Running Selenium against browser binaries installed on your laptop doesn't
scale: CI runners need matching browser versions installed, and running 8
tests in parallel means 8 real browser processes fighting for the runner's
CPU/RAM. **Selenium Grid** solves this by running browsers in disposable
containers that tests connect to over the network via `Remote` WebDriver —
[`docker-compose.yml`](docker-compose.yml) defines one:

```yaml
services:
  selenium-hub:
    image: selenium/hub:4.21.0
    ports: ["4442:4442", "4443:4443", "4444:4444"]

  chrome:
    image: selenium/node-chrome:4.21.0
    shm_size: 2gb
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_NODE_MAX_SESSIONS=2
```

```bash
docker compose up -d
pytest --grid-url=http://localhost:4444/wd/hub -n auto
docker compose down
```

Pointing the driver at Grid is a one-line branch in the browser factory —
**test code and page objects don't change at all**:

```python
if grid_url:
    return webdriver.Remote(command_executor=grid_url, options=options)
```

Open `http://localhost:4444/ui` while tests run to watch live sessions —
useful for debugging a hang without adding `time.sleep`s.

**Why Grid matters for CI scalability:** it decouples "how many browser
sessions can run at once" from "how many CPU cores does the test-runner
machine have." Add more node containers (or point at a cloud Grid) and
parallel capacity scales independently of the runner. It's also what makes
local reproduction of a CI failure exact — [§11](#11-cicd-with-github-actions)
runs the identical `docker-compose.yml` in the pipeline that you run on
your own machine.

---

## 9. Retry Logic for Flaky Tests

```bash
pip install pytest-rerunfailures   # already in requirements.txt
pytest --reruns 2 --reruns-delay 1
```

A failed test is retried up to 2 more times, waiting 1 second between
attempts, before being reported as a genuine failure. Combined with
`pytest-xdist`: `pytest -n auto --reruns 2 --reruns-delay 1`.

> **Caution — reruns are a scalpel, not a rug.** `--reruns` exists to
> absorb *environmental* flakiness: a slow CDN response, a momentarily
> overloaded Grid node, a transient network blip. It must **never** be used
> to paper over a *real* bug — a genuine race condition in the app, a
> locator that's flaky because it matches the wrong element, or a test that
> depends on shared/leftover state. If a test only passes on its second or
> third attempt *consistently*, that's a signal to fix the root cause (add
> the correct explicit wait, fix test isolation, fix the app), not to bump
> `--reruns` higher. Treat every test that needs a rerun as a bug report
> against the test or the app, not noise to be muted.

This is also why the failure-diagnostics hook (next section) captures
artifacts on **every** failed attempt, not just the final one — so a test
that passes on rerun still leaves a trail explaining why it failed the
first time.

---

## 10. Failure Diagnostics: Screenshots, Page Source, Console Logs

The single biggest time sink in CI test failures is "I can't tell what
happened and I can't reproduce it locally." [`conftest.py`](conftest.py)'s
`pytest_runtest_makereport` hook fixes that by capturing three artifacts
the moment a test fails, before the driver is torn down:

```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver")
        # 1. screenshot — driver.save_screenshot(...)
        # 2. full page source — driver.page_source
        # 3. browser console logs — driver.get_log("browser")  (Chromium)
```

Artifacts land in `artifacts/<test-name>/<timestamp>.{png,html,console.log}`
— `artifacts/` is git-ignored (regenerated every run) but uploaded as a CI
build artifact (see [§11](#11-cicd-with-github-actions)). The screenshot is
also attached inline into the `pytest-html` report when one is requested:

```bash
pytest --html=report.html --self-contained-html
```

`--self-contained-html` inlines the screenshot as base64 into the single
`report.html` file, so it's shareable as one file with no separate assets
folder — convenient for pasting into a Slack thread or attaching to a bug.

Why three artifacts and not just a screenshot: a screenshot shows *what the
page looked like*, page source shows *what was actually in the DOM* (did
the element exist but render off-screen? was it the wrong element
entirely?), and console logs surface *JavaScript errors the app itself
threw* that a screenshot can never show.

---

## 11. CI/CD with GitHub Actions

[`.github/workflows/selenium-ci.yml`](.github/workflows/selenium-ci.yml)
runs on every push to `main` and every pull request:

1. Checks out the repo, sets up Python, installs `requirements.txt`
2. Starts the same Selenium Grid from `docker-compose.yml`
3. Polls `http://localhost:4444/wd/hub/status` until Grid reports ready
4. Runs the suite **headless**, **in parallel**, **against Grid**, **with
   reruns**, producing an HTML report:
   ```bash
   pytest -n auto --reruns 2 --reruns-delay 1 \
     --grid-url="$SELENIUM_GRID_URL" \
     --html=report.html --self-contained-html
   ```
5. Tears the Grid down (`if: always()`, so this runs even on failure)
6. Uploads `report.html` and `artifacts/` as build artifacts (`if: always()`,
   so you get diagnostics precisely when you need them most — on failure)

Credentials flow in as **GitHub Actions Secrets**, exactly mirroring how
`.env` works locally — never hardcoded in the workflow file:

```yaml
env:
  SAUCE_USERNAME: ${{ secrets.SAUCE_USERNAME }}
  SAUCE_PASSWORD: ${{ secrets.SAUCE_PASSWORD }}
```

**Alternative for smaller setups:** instead of `docker-compose.yml`, a
single browser can be brought up as a native GitHub Actions
[service container](https://docs.github.com/actions/using-containerized-services/about-service-containers):

```yaml
services:
  chrome:
    image: selenium/standalone-chrome:latest
    ports: ["4444:4444"]
    options: --shm-size=2gb
```

That's a reasonable simplification for a single-browser pipeline; this
tutorial uses `docker-compose.yml` throughout so the exact same Grid
definition runs identically in CI and on your own machine, and so it can
host both a Chrome and a Firefox node for real cross-browser CI runs.

---

## 12. Production Best Practices Checklist

Use this as a PR review checklist for any Selenium suite headed to production:

- [ ] **No hardcoded waits** — every wait is an explicit `WebDriverWait`
      condition (`BasePage.find`, `EC.*`), never a bare `time.sleep(n)`
- [ ] **No hardcoded secrets** — all URLs/credentials flow through
      `config.py` and environment variables; `.env` is git-ignored,
      `.env.example` is the committed template
- [ ] **Isolated test data** — tests don't depend on data left behind by
      another test, or on running in a specific order
- [ ] **Idempotent tests** — running a test once or ten times in a row
      produces the same result; tests clean up what they create (extra
      windows closed, uploaded state reset, etc.)
- [ ] **Parallel-safe fixtures** — `driver` (and anything else
      test-specific) is function-scoped; nothing is shared mutable global
      state across tests
- [ ] **Retries for environment flakiness only** — `--reruns` absorbs
      transient infra issues; it is never used to hide a real bug (§9)
- [ ] **Meaningful assertions and messages** — every `assert` says *what*
      was expected and includes an f-string message with the *actual*
      value, so a CI failure is diagnosable from the log alone
- [ ] **CI integration** — the suite runs automatically on push/PR,
      headless, and a red build blocks merge
- [ ] **Artifact capture on failure** — screenshot + page source + console
      logs are captured automatically and uploaded as CI build artifacts

---

## 13. What's Next

This tutorial pushed Selenium as far as the tool goes for most teams:
cross-browser, parallel, Dockerized, CI-integrated, and diagnosable. The
next two tutorials cover **Playwright** — a newer automation framework with
built-in auto-waiting, network interception, and typically faster,
less-flaky execution out of the box — using the same Python + pytest
foundation you just built here.

Continue to **[Tutorial 4 — Playwright Fundamentals](../04-playwright-fundamentals/README.md)**.
