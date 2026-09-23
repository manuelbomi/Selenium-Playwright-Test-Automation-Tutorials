# Tutorial 1: Test Automation Foundations — Selenium vs. Playwright & VS Code Environment Setup

Welcome to Tutorial 1 of **Selenium & Playwright Test Automation Tutorials**, a six-part series that
takes junior QA/SWE engineers from zero browser-automation experience to writing production-grade
end-to-end (E2E) tests with both Selenium and Playwright in Python.

This tutorial lays the foundation: what test automation actually is, how Selenium and Playwright
work under the hood, how to choose between them, and how to set up a real, professional VS Code
environment for writing and debugging tests. By the end, you'll run a "Hello World" test in both
frameworks against the same public demo site used throughout this series.

## Table of Contents

- [1. What Is Test Automation and E2E Browser Testing?](#1-what-is-test-automation-and-e2e-browser-testing)
- [2. What Is Selenium? History and Architecture](#2-what-is-selenium-history-and-architecture)
- [3. What Is Playwright? Architecture](#3-what-is-playwright-architecture)
- [4. Selenium vs. Playwright: Detailed Comparison](#4-selenium-vs-playwright-detailed-comparison)
- [5. VS Code Environment Setup](#5-vs-code-environment-setup)
  - [5.1 Install Python](#51-install-python)
  - [5.2 Create and Activate a Virtual Environment](#52-create-and-activate-a-virtual-environment)
  - [5.3 Recommended VS Code Extensions](#53-recommended-vs-code-extensions)
  - [5.4 Install Selenium and Its Dependencies](#54-install-selenium-and-its-dependencies)
  - [5.5 Install Playwright and Its Dependencies](#55-install-playwright-and-its-dependencies)
  - [5.6 Recommended Project Folder Structure](#56-recommended-project-folder-structure)
  - [5.7 VS Code Workspace Configuration Files](#57-vs-code-workspace-configuration-files)
  - [5.8 Running Tests: Testing Sidebar vs. Terminal](#58-running-tests-testing-sidebar-vs-terminal)
- [6. Hello World: Selenium](#6-hello-world-selenium)
- [7. Hello World: Playwright](#7-hello-world-playwright)
- [8. What's Next](#8-whats-next)

---

## 1. What Is Test Automation and E2E Browser Testing?

**Test automation** is the practice of using software to execute tests against your application and
verify the results, instead of a human manually clicking through the app every time. It spans many
levels:

- **Unit tests** — test a single function or class in isolation (milliseconds, no browser).
- **Integration tests** — test how multiple components work together (e.g., a service talking to a
  database).
- **End-to-end (E2E) tests** — drive a *real browser* through your actual UI the way a real user
  would: click buttons, fill forms, navigate pages, and assert that the right thing appears on
  screen. This is the layer Selenium and Playwright operate at.

E2E browser testing is uniquely valuable because it's the closest thing to "does this actually work
for a real user?" A unit test can prove your `calculate_total()` function returns the right number,
but only an E2E test can prove that clicking "Add to Cart" on the real rendered page actually updates
the cart badge, persists across a page reload, and lets the user complete checkout.

### Why E2E testing matters in a CI/CD pipeline

Modern software teams ship continuously — often multiple times a day — using **CI/CD** (Continuous
Integration / Continuous Delivery) pipelines. Every time a developer pushes code, an automated
pipeline builds the app, runs the test suite, and only allows deployment if everything passes. E2E
browser tests plug into this pipeline as a critical safety net:

- **They catch regressions unit tests can't.** A CSS change, a broken JavaScript bundle, a backend
  API contract change — these often only surface when a real browser renders the real page.
- **They run on every pull request**, so a broken checkout flow is caught *before* merge, not
  discovered by a customer in production.
- **They enable confident, frequent deployments.** Without automated E2E coverage, teams either ship
  slowly (relying on manual QA) or ship recklessly (skipping verification). Automation lets you do
  neither — you ship fast *and* verified.
- **They run headless and in parallel** on CI infrastructure (e.g., GitHub Actions, Jenkins,
  Azure DevOps), so a full regression suite that would take a human QA engineer days can run in
  minutes across many machines simultaneously.

This series will build toward exactly that: by Tutorial 6, you'll have production-grade Selenium and
Playwright suites structured to run reliably in CI. But everything starts with understanding the two
tools you'll be using — so let's get into how each one actually works.

---

## 2. What Is Selenium? History and Architecture

**Selenium** is the original, most widely adopted browser automation framework. It began in 2004 as
an internal tool at ThoughtWorks (originally called "Selenium Core," a JavaScript-based tool for
testing a web app by embedding it in the page itself). In 2006, Google engineer Simon Stewart created
**WebDriver**, a framework that controlled browsers natively (via each browser's own automation
hooks) rather than injecting JavaScript into the page. In 2009, Selenium and WebDriver merged into
**Selenium WebDriver**, which became a W3C web standard (the **WebDriver protocol**) in 2018. Selenium
is now on major version 4, fully built on that W3C standard, and remains the most battle-tested,
broadly-supported browser automation tool in existence — with bindings for Java, Python, C#,
JavaScript, Ruby, Kotlin, and more.

### The WebDriver protocol architecture

Understanding Selenium's architecture explains almost everything about how you'll write and debug
Selenium tests. There are three distinct layers:

```
Your Python test code
        |
        |  (Python method calls, e.g. driver.get(url), element.click())
        v
Selenium client bindings (the `selenium` pip package)
        |
        |  translates each call into an HTTP request following the
        |  W3C WebDriver wire protocol (JSON over HTTP)
        v
Browser driver executable (e.g. chromedriver.exe, geckodriver)
        |
        |  a separate background process that receives HTTP requests
        |  and translates them into low-level, browser-specific
        |  automation commands
        v
The actual browser (Chrome, Firefox, Edge, Safari)
```

1. **Client bindings** — When you write `driver.get("https://www.saucedemo.com/")` in Python, the
   `selenium` library doesn't talk to the browser directly. It serializes that call into a JSON HTTP
   request (per the W3C WebDriver spec) and sends it to a local server.
2. **Driver executable** — That local server is a separate binary — `chromedriver` for Chrome,
   `geckodriver` for Firefox, `msedgedriver` for Edge, etc. — that Selenium starts as its own OS
   process. The driver receives the HTTP request, translates it into whatever proprietary automation
   API that specific browser exposes, and executes it.
3. **The browser** — The driver executable controls the real, actual browser application, which
   renders the page and performs the requested action (navigation, click, type, etc.). The result is
   sent back up the chain: browser → driver → HTTP response → Python client → your test code.

### Why a separate driver binary is needed

Because Selenium standardizes on one *protocol* (WebDriver) rather than one *implementation*, each
browser vendor ships (or a community maintains) its own driver executable that speaks WebDriver on one
side and that browser's native automation hooks on the other. This is powerful for
standardization — the same Selenium test code can target Chrome, Firefox, or Edge just by swapping
which driver executable you start — but it comes with real operational cost:

- You must have the *correct version* of the driver binary installed, matched to your *installed
  browser version*. A mismatch (e.g., chromedriver 120 trying to control Chrome 127) causes
  connection failures.
- Every time your browser auto-updates, you may need to re-download a matching driver.
- Historically, engineers downloaded these binaries manually and either placed them on the system
  `PATH` or pointed Selenium at their file path explicitly — tedious and error-prone, and a common
  source of "works on my machine" CI failures.

This is precisely the pain point that `webdriver-manager` (which you'll install in section 5.4)
solves: it automatically detects your installed browser version and downloads/caches the matching
driver binary for you, so you never touch this problem by hand.

---

## 3. What Is Playwright? Architecture

**Playwright** is a newer (first released in 2020) browser automation framework built by Microsoft,
created by many of the same engineers who originally built Google's Puppeteer project. It was
designed from the ground up to address friction points teams had accumulated with Selenium after over
a decade of real-world use — particularly around flaky waits, multi-browser/multi-tab testing, and
the driver-binary management problem described above.

### Architecture: no separate driver binary

Playwright's biggest architectural difference from Selenium is that **there is no separate driver
executable process that you manage**. Instead:

```
Your Python test code
        |
        |  (Python method calls, e.g. page.goto(url), page.click(selector))
        v
Playwright client library (the `playwright` pip package)
        |
        |  communicates directly with the browser over a persistent
        |  WebSocket connection, using each browser's own remote-debugging
        |  protocol (CDP for Chromium; browser-specific equivalents for
        |  Firefox/WebKit, patched into Playwright's own browser builds)
        v
The actual browser (Chromium, Firefox, or WebKit)
```

Playwright still launches a browser process, but it talks to it *directly* via a low-level protocol
(most famously the **Chrome DevTools Protocol**, or **CDP**, for Chromium-based browsers) over a
WebSocket, rather than round-tripping through a separate HTTP driver executable. Practically, this
means:

- Running `playwright install` (section 5.5) downloads Playwright's own tested, version-matched
  browser binaries once — there's no ongoing "does my driver version match my browser version"
  problem, because Playwright ships and manages both the library *and* the browsers together.
- Fewer moving parts generally means faster execution and fewer version-mismatch failures.
- Playwright can patch its bundled Firefox and WebKit builds with extra automation hooks that
  wouldn't be available in a stock consumer browser, enabling more reliable control.

### The Browser → Context → Page model

Playwright organizes automation around three nested concepts, and understanding this hierarchy is
essential to using Playwright well:

- **Browser** — one running instance of a browser engine (Chromium, Firefox, or WebKit). Launching a
  browser is relatively expensive (real OS process, real memory), so tests typically share one
  browser instance across many tests.
- **Browser Context** — an isolated, incognito-like session *within* that browser: its own cookies,
  local storage, session storage, and cache, completely walled off from every other context. Creating
  a new context is cheap and fast (much cheaper than launching a whole new browser process).
- **Page** — a single tab/window living inside a context. A context can hold multiple pages at once,
  which is how you test multi-tab flows (e.g., "click a link that opens a new tab").

```
Browser (Chromium process)
 ├── Context A  (isolated cookies/storage)
 │    ├── Page 1
 │    └── Page 2  (e.g., a second tab opened by clicking a link)
 └── Context B  (a completely separate isolated session)
      └── Page 1
```

### Why contexts give test isolation

In Selenium, the common pattern for isolating tests from each other is to launch a *brand-new browser
process* per test (or carefully clear cookies/storage between tests) — because a single browser
window's cookies and storage are shared globally within that window. Launching a new browser process
is slow: it has real startup cost.

Playwright's context model gives you that same isolation — Test A's login session can never leak
into Test B's — **without** paying the cost of a new browser process every time. You launch one
browser (once, ideally shared across a whole test run) and then create a fresh, isolated context per
test in milliseconds. This is a major reason Playwright test suites tend to run faster than equivalent
Selenium suites at scale.

---

## 4. Selenium vs. Playwright: Detailed Comparison

There's no universally "better" tool — they have different strengths. Use this table to reason about
tradeoffs for your specific project.

| Dimension | Selenium | Playwright |
|---|---|---|
| **Speed** | Slower on average — every command is an HTTP round-trip through a separate driver process; isolating tests often means launching new browser processes. | Faster — direct WebSocket connection to the browser, cheap context creation instead of full browser relaunch for isolation. |
| **Auto-waiting** | Limited/manual — historically required explicit `WebDriverWait` + expected-condition code to avoid flaky "element not interactable" errors (covered in depth in Tutorial 2/3). | Built-in — Playwright automatically waits for elements to be visible, stable, and actionable before interacting, dramatically reducing flaky tests out of the box. |
| **Multi-tab / multi-context support** | Possible via window handles (`driver.switch_to.window(...)`), but manual and easy to get wrong. | First-class — the Browser/Context/Page model is designed around this; multiple isolated contexts and multiple tabs per context are natural. |
| **Network interception / mocking** | Limited natively; typically requires a proxy tool (e.g., BrowserMob Proxy, Selenium Wire) bolted on. | Built-in — `page.route()` lets you intercept, modify, block, or mock network requests/responses directly. |
| **Mobile emulation** | Possible via Chrome DevTools mobile emulation flags, but Chrome-specific and less integrated. | Built-in device descriptors (e.g., `playwright.devices["iPhone 13"]`) covering viewport, user agent, and touch support across browsers. |
| **Language bindings** | Java, Python, C#, JavaScript/TypeScript, Ruby, Kotlin — the broadest official support of any tool in this space. | Python, JavaScript/TypeScript, Java, C# — fewer languages, but all first-party maintained by the Playwright team itself. |
| **Browser engine coverage** | Real, consumer-grade Chrome, Firefox, Edge, Safari (via SafariDriver) — you automate the actual browser your users run. | Chromium, Firefox, and WebKit engines, but via Playwright's own bundled builds (very close to, but not byte-identical to, consumer Chrome/Safari releases). |
| **Community / maturity** | Extremely mature (20+ years); the largest ecosystem of tutorials, Stack Overflow answers, grid/cloud providers, and enterprise adoption. | Newer (since 2020) but growing very fast, with strong first-party documentation and rapidly increasing enterprise adoption. |
| **Licensing** | Open source, Apache 2.0. | Open source, Apache 2.0. |
| **Driver/browser management** | Manual driver binary management (mitigated by `webdriver-manager`, section 5.4). | Managed automatically via `playwright install` — no separate driver binaries at all. |
| **Typical use cases** | Large legacy test suites; teams needing Safari coverage or non-JS/Python/Java/C# language bindings; environments standardized on Selenium Grid / cloud grids (BrowserStack, Sauce Labs) for real-device/browser coverage. | New projects prioritizing speed and low test flakiness; teams that want built-in network mocking and multi-tab testing without extra tooling; projects fine with Chromium/Firefox/WebKit engine coverage instead of consumer Safari. |

### When to pick which (or use both)

- **Choose Playwright** if you're starting a new project, want the fastest, least-flaky test suite
  out of the box, need first-class network interception or mobile emulation, or want the simplest
  setup story (no driver binaries).
- **Choose Selenium** if you need real Safari automation, need a language binding Playwright doesn't
  officially support, are integrating with an existing Selenium Grid / cloud device-lab investment, or
  are working in a codebase that already has a mature Selenium suite where a full rewrite isn't
  justified.
- **Use both** — many real teams do. A common pattern: Selenium for a legacy regression suite that
  isn't worth rewriting, and Playwright for all new test development. This series intentionally
  teaches you both (Selenium in Tutorials 2–3, Playwright in Tutorials 4–5) so you're equipped to work
  on either kind of codebase professionally, and can make this tradeoff call yourself on the job.

---

## 5. VS Code Environment Setup

This section walks through building a real, professional automation environment from scratch. Follow
it in order — later steps assume earlier ones are done.

### 5.1 Install Python

You need **Python 3.10 or newer**.

- **Windows**: Download the installer from [python.org/downloads](https://www.python.org/downloads/).
  During installation, **check the box "Add python.exe to PATH"** on the first screen — this is the
  single most common setup mistake and causes `python` to be "not recognized" in the terminal
  afterward.
- **macOS**: Install via [python.org](https://www.python.org/downloads/) or Homebrew:
  ```bash
  brew install python@3.12
  ```
- **Linux (Debian/Ubuntu)**:
  ```bash
  sudo apt update && sudo apt install python3 python3-venv python3-pip
  ```

Verify the install in a terminal:

```bash
python --version
```

> **Note (macOS/Linux):** some systems only expose `python3` (not `python`) by default. If
> `python --version` fails, try `python3 --version` instead — you'll use whichever command works
> consistently through the rest of this tutorial.

Expected output looks like:

```text
Python 3.12.4
```

Anything `3.10.x` or higher is fine for this entire tutorial series.

### 5.2 Create and Activate a Virtual Environment

A **virtual environment** (venv) is an isolated, project-local Python installation. It keeps this
tutorial's dependencies (selenium, playwright, pytest, etc.) separate from your system Python and from
other projects' dependencies — avoiding version conflicts entirely. **Always use a venv for real
projects.**

Open a terminal **inside this tutorial's folder**
(`01-foundations-and-environment-setup/`) and create the venv:

```bash
python -m venv .venv
```

This creates a `.venv/` folder containing a private copy of the Python interpreter and its own
`site-packages` directory for installed libraries.

Now **activate** it. The activation command differs by shell/OS:

**Windows — PowerShell** (VS Code's default integrated terminal on Windows):

```powershell
.venv\Scripts\Activate.ps1
```

> If PowerShell blocks the script with an "execution policy" error, run this once (per user, it's
> safe) and then retry activation:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

**Windows — Command Prompt (cmd.exe):**

```bat
.venv\Scripts\activate.bat
```

**macOS / Linux — bash or zsh:**

```bash
source .venv/bin/activate
```

You'll know it worked because your terminal prompt is prefixed with `(.venv)`. From this point
forward, `python` and `pip` refer to the venv's private copies — anything you install with `pip` goes
into `.venv/`, not your system Python.

To leave the venv later, run `deactivate` (same command on every OS/shell).

### 5.3 Recommended VS Code Extensions

Install these from the VS Code Extensions sidebar (`Ctrl+Shift+X` / `Cmd+Shift+X`):

| Extension | Publisher ID | Why it helps |
|---|---|---|
| **Python** | `ms-python.python` | Core VS Code Python support: interpreter selection, running/debugging scripts, integrates with the Testing sidebar for pytest. Without it, none of the setup below (`launch.json`, `settings.json`, Testing sidebar) works. |
| **Pylance** | (bundled with/installed alongside `ms-python.python`) | Fast, accurate autocomplete, type checking, and "go to definition" for Python. Essential for productively exploring the `selenium` and `playwright` APIs as you learn them — hover over any method to see its signature and docstring instantly. |
| **Playwright Test for VSCode** | `ms-playwright.playwright` | Adds a dedicated Playwright test runner integration: run/debug individual Playwright tests directly from the editor gutter, auto-generate selectors by picking elements in a live browser ("Pick locator"), and view trace files (a full recording of a test run) inside VS Code. Extremely useful once we start writing real Playwright test suites in Tutorial 4. |

Install each by searching its publisher ID (e.g. `ms-python.python`) in the Extensions search box and
clicking **Install**.

### 5.4 Install Selenium and Its Dependencies

With your venv **activated** (prompt shows `(.venv)`), install from this tutorial's
`requirements.txt`:

```bash
pip install -r requirements.txt
```

That single command installs everything for both frameworks. If you want to understand the Selenium
pieces individually, they are:

```bash
pip install selenium webdriver-manager pytest pytest-html
```

- **`selenium`** — the client bindings library described in section 2 (the layer your Python code
  calls directly).
- **`webdriver-manager`** — as explained in section 2, Selenium needs a browser-specific driver
  executable (e.g. `chromedriver`) that matches your installed browser version. `webdriver-manager`
  detects your installed Chrome (or Firefox/Edge) version automatically, downloads the matching driver
  binary, caches it locally, and hands Selenium its file path — so you never manually download,
  place-on-PATH, or version-match a driver binary yourself. This is the modern, recommended approach
  and is what `hello_selenium.py` (section 6) uses.
- **`pytest`** — the test runner we'll use starting in Tutorial 2 to structure real test suites
  (fixtures, assertions, parametrization, test discovery).
- **`pytest-html`** — generates a single, shareable HTML report summarizing a pytest run (pass/fail
  counts, tracebacks, timing) — useful for CI artifacts and for showing test results to non-engineers.

### 5.5 Install Playwright and Its Dependencies

Already covered by `pip install -r requirements.txt` above. Individually:

```bash
pip install playwright pytest-playwright
```

- **`playwright`** — the Playwright client library itself.
- **`pytest-playwright`** — a pytest plugin that provides ready-made fixtures (`page`, `browser`,
  `context`, etc.) so you can write Playwright tests as plain pytest functions without wiring up
  browser launch/teardown by hand. We'll use this starting in Tutorial 4.

Installing the `playwright` Python package does **not** download any actual browser binaries. You
must run one more command:

```bash
playwright install
```

**What this command does:** it downloads Playwright's own tested, version-matched browser
binaries — Chromium, Firefox, and WebKit — into a local cache directory (`~/.cache/ms-playwright` on
macOS/Linux, `%USERPROFILE%\AppData\Local\ms-playwright` on Windows) and, on Linux, may also need
`playwright install-deps` to install OS-level shared libraries those browsers depend on. This is the
Playwright equivalent of what `webdriver-manager` does for Selenium — except Playwright manages *all
three* browser engines through one command, and re-running it later keeps them updated. If you only
need Chromium (faster download, smaller disk footprint) for now, you can scope it:

```bash
playwright install chromium
```

Both `hello_playwright.py` (section 7) and every Playwright example later in this series assume
you've run `playwright install` at least once.

### 5.6 Recommended Project Folder Structure

This tutorial's own folder is structured the way a real automation repo should be — use it as the
template for the rest of this series (and for your own projects):

```text
01-foundations-and-environment-setup/
├── .vscode/
│   ├── settings.json      # Points VS Code at the venv interpreter; configures pytest discovery
│   └── launch.json         # Debug config for running the current test file with breakpoints
├── examples/
│   ├── hello_selenium.py   # Standalone Selenium "Hello World" script
│   └── hello_playwright.py # Standalone Playwright "Hello World" script
├── requirements.txt         # Pinned-minimum Python dependencies for this tutorial
└── README.md                 # This file
```

As the series progresses (Tutorials 2–6), later folders will add `tests/` (pytest test files),
`pages/` (Page Object Model classes), and `conftest.py` (shared pytest fixtures) alongside this same
`.vscode/` + `requirements.txt` pattern — so getting comfortable with this layout now pays off
immediately in Tutorial 2.

### 5.7 VS Code Workspace Configuration Files

This tutorial folder already includes both files described below — open them in VS Code to see them
in context.

**`.vscode/settings.json`** points the Python extension at your venv's interpreter, so VS Code's
IntelliSense, linting, and test discovery all use the exact same Python environment you installed
your dependencies into:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": ["."]
}
```

> **macOS/Linux users:** change `"${workspaceFolder}/.venv/Scripts/python.exe"` to
> `"${workspaceFolder}/.venv/bin/python"` — the venv's internal folder layout differs by OS
> (`Scripts/` + `.exe` on Windows vs. `bin/` with no extension on macOS/Linux).

**`.vscode/launch.json`** defines a debug configuration that runs *whichever test file is currently
open* under the debugger, so you can set breakpoints and step through Selenium/Playwright code line by
line:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Debug Current pytest File",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": ["${file}", "-v", "-s"],
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

To use it: open a test file, click in the gutter to the left of a line number to set a breakpoint (a
red dot appears), then open the **Run and Debug** panel (`Ctrl+Shift+D` / `Cmd+Shift+D`) and click the
green ▶ next to **"Python: Debug Current pytest File."** Execution will pause at your breakpoint,
letting you inspect variables (e.g., what a Selenium `WebElement` or Playwright `Locator` actually
found) in the Debug sidebar.

### 5.8 Running Tests: Testing Sidebar vs. Terminal

Once `python.testing.pytestEnabled` is set (section 5.7) and your venv has `pytest` installed:

**From the VS Code Testing sidebar:**

1. Click the flask/beaker icon in the left Activity Bar (or `Ctrl+Shift+T`).
2. VS Code auto-discovers any `test_*.py` files and displays them in a tree.
3. Click the ▶ next to any test, class, or file to run it — or the ▶ at the top to run everything.
4. Results show inline (green check / red X), and clicking a failed test jumps straight to the
   assertion that failed.

**From the terminal** (with the venv activated):

```bash
pytest
```

Useful flags you'll use constantly throughout this series:

```bash
pytest -v                       # verbose: show each test's name and result
pytest -s                       # don't capture stdout — see print()/console output live
pytest tests/test_login.py      # run only one file
pytest -k "login"                # run only tests whose name contains "login"
pytest --html=report.html       # generate an HTML report (needs pytest-html, already installed)
```

Both approaches run the exact same tests — the Testing sidebar is convenient during development
(fast feedback, click-to-debug), while the terminal command is what your CI pipeline will actually
run.

---

## 6. Hello World: Selenium

Open [`examples/hello_selenium.py`](examples/hello_selenium.py). Here's what each part does — read
this alongside the file:

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

SAUCE_DEMO_URL = "https://www.saucedemo.com/"

def run_hello_selenium() -> None:
    driver = None
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        driver.get(SAUCE_DEMO_URL)
        assert "Swag Labs" in driver.title
        print("SUCCESS")
    finally:
        if driver is not None:
            driver.quit()

if __name__ == "__main__":
    run_hello_selenium()
```

Line by line:

- `from selenium import webdriver` — imports Selenium's entry point for launching and controlling
  browsers.
- `ChromeDriverManager().install()` — downloads (or reuses a cached) `chromedriver` binary
  version-matched to your installed Chrome, and returns its filesystem path. This is the piece that
  eliminates manual driver-binary management (section 2 explains why this binary is needed at all).
- `webdriver.Chrome(service=service)` — actually launches Chrome, starting the driver executable as a
  background process that the Selenium client then talks to over HTTP (the WebDriver protocol from
  section 2's architecture diagram).
- `driver.get(SAUCE_DEMO_URL)` — navigates the browser and blocks until the initial page load
  completes.
- `assert "Swag Labs" in driver.title` — a smoke-test assertion: SauceDemo's `<title>` tag reads
  "Swag Labs," so this confirms the right page actually loaded.
- `finally: driver.quit()` — **always** runs, even if the assertion above fails or any other
  exception is raised. This is the correct, safe way to clean up a Selenium session: `driver.quit()`
  closes the browser window *and* terminates the driver executable process. Skipping this (or only
  calling it on the "happy path") is a common beginner mistake that leaves orphaned browser/driver
  processes running in the background.

Run it:

```bash
python examples/hello_selenium.py
```

Expected output:

```text
SUCCESS: Selenium launched Chrome and loaded SauceDemo correctly.
Page title was: 'Swag Labs'
```

You should briefly see a real Chrome window open, navigate to SauceDemo, then close automatically.

---

## 7. Hello World: Playwright

Open [`examples/hello_playwright.py`](examples/hello_playwright.py). Here's the equivalent walkthrough:

```python
from playwright.sync_api import sync_playwright

SAUCE_DEMO_URL = "https://www.saucedemo.com/"

def run_hello_playwright() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(SAUCE_DEMO_URL)
        title = page.title()
        assert "Swag Labs" in title
        print("SUCCESS")
        browser.close()

if __name__ == "__main__":
    run_hello_playwright()
```

Line by line:

- `from playwright.sync_api import sync_playwright` — imports the synchronous (blocking) Playwright
  API, the simplest entry point for engineers new to browser automation.
- `with sync_playwright() as p:` — starts the Playwright driver process and, critically, **guarantees
  it shuts down cleanly when this block exits**, even if an exception occurs inside it. This is the
  direct structural replacement for Selenium's manual `try/finally: driver.quit()` — Playwright's
  context-manager pattern makes correct cleanup the *default*, not something you have to remember to
  code yourself.
- `p.chromium.launch(headless=False)` — launches a real Chromium browser process.
  `headless=False` means you see the window; in CI you'd typically use the default `headless=True`
  for speed.
- `browser.new_context()` — creates an isolated session (its own cookies/storage) inside that browser
  process, as described in section 3's Browser → Context → Page model.
- `context.new_page()` — opens a new tab inside that context.
- `page.goto(SAUCE_DEMO_URL)` — navigates the page. Playwright auto-waits for the page to reach a
  stable load state before returning, which is why Playwright scripts generally need fewer manual
  waits than Selenium (see the comparison table in section 4).
- `assert "Swag Labs" in title` — the same smoke-test assertion as the Selenium version, so the two
  scripts are directly comparable.
- `browser.close()` — explicitly closes the browser for prompt cleanup. Note that even without this
  line, exiting the `with sync_playwright() as p:` block still tears down the underlying Playwright
  connection cleanly — there's no equivalent risk of an orphaned driver process that Selenium has if
  you forget `driver.quit()`.

Run it:

```bash
python examples/hello_playwright.py
```

Expected output:

```text
SUCCESS: Playwright launched Chromium and loaded SauceDemo correctly.
Page title was: 'Swag Labs'
```

Same expected behavior as the Selenium version: a browser window opens, loads SauceDemo, and closes.

---

## 8. What's Next

You now understand *why* E2E browser testing matters, *how* Selenium and Playwright each work under
the hood, *when* to reach for each one, and you have a working, properly configured VS Code
environment with both frameworks installed and verified.

From here, the series branches into two parallel tracks so you can build real depth in each tool:

- **[Tutorial 2 — Selenium Fundamentals](../02-selenium-fundamentals/README.md)**: locators
  (`By.CSS_SELECTOR`, `By.XPATH`, etc.), explicit vs. implicit waits, the Page Object Model pattern,
  and structuring real pytest-based Selenium test suites.
- **[Tutorial 4 — Playwright Fundamentals](../04-playwright-fundamentals/README.md)**: Playwright
  locators and auto-waiting in depth, `pytest-playwright` fixtures, assertions with `expect()`, and
  the Playwright equivalent of the Page Object Model.

Tutorials 3 and 5 build on those with advanced, production-grade patterns (retries, parallelization,
CI integration, visual/network testing) for each framework respectively, and Tutorial 6 closes the
series with AI-agent-driven automation using MCP and Claude Code. See you in Tutorial 2 or 4!
