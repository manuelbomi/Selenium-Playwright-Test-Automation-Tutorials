# Tutorial 5: Advanced Playwright — Network Interception, Visual Testing, Parallelization & CI/CD

Tutorial 4 got you a working Playwright + pytest suite: contexts and pages,
role-based locators, auto-waiting, `expect()` assertions, and a Page Object
Model against [saucedemo.com](https://www.saucedemo.com/). That's enough to
replace a Selenium suite one-for-one.

This tutorial is about the gap between "a working test suite" and "a
production-grade automation framework" — the stuff that separates tests
that run on your laptop from tests that run reliably, in parallel, in CI,
for a whole team, for months. Several of the techniques here (network
interception, trace-based debugging, built-in multi-engine support) are
things **Selenium cannot do natively at all** — we'll call those out as we
go, since they're a big part of why teams migrate.

Everything below targets <https://www.saucedemo.com/> (login
`standard_user` / `secret_sauce`), same as Tutorial 4, so you can build
directly on what you already know.

## Table of Contents

1. [Prerequisites & Setup](#prerequisites--setup)
2. [Why This Matters: Playwright vs. Selenium at the Advanced Level](#why-this-matters-playwright-vs-selenium-at-the-advanced-level)
3. [Network Interception & Mocking with `page.route()`](#network-interception--mocking-with-pageroute)
4. [API Testing with the `request` Fixture / `APIRequestContext`](#api-testing-with-the-request-fixture--apirequestcontext)
5. [Authentication State Reuse via `storage_state`](#authentication-state-reuse-via-storage_state)
6. [Visual Regression Testing](#visual-regression-testing)
7. [Multi-Browser & Device Emulation](#multi-browser--device-emulation)
8. [Parallelization & Sharding](#parallelization--sharding)
9. [Dockerizing Playwright Tests](#dockerizing-playwright-tests)
10. [CI/CD with GitHub Actions](#cicd-with-github-actions)
11. [Test Data & Environment Config via `.env`](#test-data--environment-config-via-env)
12. [Debugging with the Trace Viewer (Deep Dive)](#debugging-with-the-trace-viewer-deep-dive)
13. [Production Best Practices Checklist](#production-best-practices-checklist)
14. [What's Next](#whats-next)

---

## Prerequisites & Setup

You've completed [Tutorial 4](../04-playwright-fundamentals/README.md) or
are comfortable with: Playwright contexts/pages, locators, `expect()`, and
running `pytest` with `pytest-playwright`.

```bash
# From this directory: 05-playwright-advanced-production-patterns/
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
playwright install --with-deps   # downloads chromium/firefox/webkit + OS deps

cp .env.example .env             # then edit if you need non-default values
```

Sanity check:

```bash
pytest -v
```

The first run will fail on `test_visual.py` (no baseline screenshot exists
yet) — that's expected and covered in the
[Visual Regression Testing](#visual-regression-testing) section below.

---

## Why This Matters: Playwright vs. Selenium at the Advanced Level

At the basics (find element, click, assert text), Playwright and Selenium
are roughly interchangeable — Tutorial 4 could have been written against
either tool with different syntax. **At the advanced level, they diverge
sharply**, because Playwright was built from scratch around a
browser-controlled-via-CDP (Chrome DevTools Protocol)-style architecture,
while Selenium was built around the WebDriver protocol (a standardized,
but more limited, remote-control API). Concretely, this tutorial covers
several things Selenium has **no native equivalent** for:

| Capability | Playwright | Selenium |
|---|---|---|
| Intercept/mock network requests | Built in (`page.route()`) | Not supported natively — requires an external proxy (e.g. BrowserMob Proxy) |
| Pure HTTP API calls sharing browser cookies | Built in (`APIRequestContext`) | Not supported — needs a separate HTTP client, manual cookie sync |
| Record a full execution trace (DOM snapshots, network, console, screenshots per action) | Built in (Trace Viewer) | Not supported — logs only, no visual trace |
| Auto-waiting for actionability | Built in for all actions | Partial — requires explicit `WebDriverWait` for most conditions |
| One test, three browser engines | Built in (Chromium, Firefox, WebKit ship with the library) | Requires separate driver binaries per browser, version-matched by hand |

Everything below leans on these differentiators. Keep that table in mind —
it's the "why" behind most of this tutorial.

---

## Network Interception & Mocking with `page.route()`

`page.route(url_pattern, handler)` lets you intercept any request the page
makes and decide what happens to it: let it through unmodified
(`route.continue_()`), block it (`route.abort()`), or **fake the response
entirely** (`route.fulfill()`) — all without the real backend knowing or
caring.

Why this matters in production suites:

- **Testing error states on demand.** You want to verify the UI shows a
  friendly "Something went wrong, please try again" message when the
  product API returns a 500. Waiting for a real outage, or standing up a
  broken backend, isn't practical. `route.fulfill(status=500, ...)` gives
  you that error state whenever you want it.
- **Removing flakiness that isn't yours to fix.** A page that calls a
  third-party analytics or ads endpoint can make your test flaky for
  reasons that have nothing to do with the feature under test. Block or
  mock those calls.
- **Testing edge cases the real backend can't easily produce**, like a
  slow response (`route.fulfill()` after an artificial delay), a malformed
  JSON body, or a partial/empty result set.

```python
def fail_request(route):
    route.fulfill(
        status=500,
        content_type="application/json",
        body='{"error": "internal server error"}',
    )

page.route("**/api/products", fail_request)
```

saucedemo.com is a static demo with no real JSON API (its inventory is
hardcoded client-side JS), so [`tests/test_network_mocking.py`](tests/test_network_mocking.py)
demonstrates the exact same mechanism against the most realistic
interceptable request the app *does* make — its product image requests —
mocking a 500 and asserting the page still renders critical content (names,
prices) even though a dependent resource failed. The technique — match a
URL, fulfill with a controlled response, assert on the resulting UI state —
transfers directly to a real JSON API; only the URL pattern and response
body change. Run it:

```bash
pytest tests/test_network_mocking.py -v
```

---

## API Testing with the `request` Fixture / `APIRequestContext`

Playwright ships an HTTP client — `APIRequestContext` — that makes real
network calls **without launching a browser at all**. `pytest-playwright`
exposes it as the `request` fixture. This matters for two distinct use
cases:

1. **Testing a JSON API directly.** If the app under test exposes a REST/
   GraphQL API, you can assert on status codes, response bodies, and
   headers directly — far faster than driving a browser, and not coupled
   to any UI implementation detail.
2. **Setting up or tearing down test state without clicking through the
   UI.** This is the bigger production win. If a test needs "a cart with 3
   items" or "a user with an existing order," creating that state by
   clicking through the UI is slow and fragile — every UI step is another
   chance for the test to flake on something unrelated to what's actually
   being tested. Where the app has an API, call it directly to set up
   state, then use the browser only for the behavior you actually want to
   verify.

```python
def test_healthcheck(request):
    # No browser launched at all -- just an HTTP call.
    response = request.get("https://www.saucedemo.com/")
    assert response.status == 200
    assert response.ok
```

A same-origin `request` call inside a test that also uses `page` **shares
cookies with the browser context** when made through `context.request`
(rather than the standalone top-level `request` fixture) — meaning you can
log in once via the UI (or via `storage_state`, see next section), then use
`context.request.post(...)` to seed data as that authenticated user, no
extra auth plumbing required:

```python
def test_seed_via_api_then_verify_in_ui(authenticated_context):
    # Same session/cookies as the browser context -- no separate auth needed.
    response = authenticated_context.request.get("/inventory.html")
    assert response.ok

    page = authenticated_context.new_page()
    page.goto("/inventory.html")
    # ... assertions against the UI, having skipped an extra UI round trip
```

**Rule of thumb:** if a test's job is to verify behavior X, use the API (or
`storage_state`) for everything that *isn't* X, and reserve the browser for
the part that is. saucedemo has no real API to demonstrate this against
end-to-end, but the pattern above is exactly how you'd wire it up against a
real backend.

---

## Authentication State Reuse via `storage_state`

This is one of the highest-leverage techniques in this tutorial. Every
Playwright `BrowserContext` can save its cookies and `localStorage` to a
JSON file (`context.storage_state(path=...)`) and, separately, a **new**
context can be created pre-loaded with that same state
(`browser.new_context(storage_state=...)`). Log in once, reuse the session
everywhere.

**Why it matters:** in a Selenium (or naive Playwright) suite, every test
class typically logs in from scratch in `setUp()`. Multiply a 3-second login
flow by a few hundred tests and you've added minutes to every CI run — and
every one of those logins is a chance for the test to flake on something
that has nothing to do with what the test is actually checking. Log in
*once*, save the session, and every test that needs to be authenticated
just loads it.

This repo implements the full pattern:

- [`auth_setup/generate_auth_state.py`](auth_setup/generate_auth_state.py) —
  a standalone script that launches a browser, logs into saucedemo.com
  through the real UI (once), and saves the resulting session to
  `auth_setup/state.json`.
- [`conftest.py`](conftest.py) — the `authenticated_context` /
  `authenticated_page` fixtures load that file into a fresh
  `browser.new_context(storage_state=...)`, generating it on the fly (by
  invoking the setup script) if it doesn't exist yet.

```python
# conftest.py (excerpt)
@pytest.fixture
def authenticated_context(browser, base_url):
    _ensure_auth_state_exists()  # runs generate_auth_state.py if missing
    context = browser.new_context(storage_state=str(STATE_PATH), base_url=base_url)
    yield context
    context.close()
```

[`tests/test_authenticated_flow.py`](tests/test_authenticated_flow.py) shows
the payoff: it navigates straight to `/inventory.html` and adds an item to
the cart — **no login step anywhere in the test.**

```bash
pytest tests/test_authenticated_flow.py -v
```

**Production notes:**

- `auth_setup/state.json` is gitignored (see [`.gitignore`](.gitignore)) —
  it's live session data, not something to check into source control, even
  against a throwaway demo site. Treat it like any other credential.
- In CI, regenerate the state file at the start of the job (or cache it for
  a short TTL) rather than committing a long-lived one — sessions expire,
  and a stale `state.json` produces confusing "why am I logged out"
  failures days later.
- If your app has multiple roles (admin, standard user, read-only), save a
  separate state file per role and parametrize which one a given test
  fixture loads.

---

## Visual Regression Testing

`expect(page).to_have_screenshot()` captures a screenshot and compares it
pixel-by-pixel against a checked-in **baseline** image, failing the test if
the difference exceeds a tolerance. This catches an entire category of bug
that functional/DOM assertions miss entirely: broken CSS layout, an
overlapping element, a font that silently failed to load, a color
regression.

[`tests/test_visual.py`](tests/test_visual.py) runs this against the
saucedemo login page.

**How baselines work:**

1. First run: no baseline exists yet, so the test fails with a "no baseline
   found" message and writes the screenshot it captured to
   `tests/test_visual.py-snapshots/`.
2. Review that image. If it's correct, promote it to the baseline:

   ```bash
   pytest tests/test_visual.py --update-snapshots
   ```

3. Commit the resulting PNG under `tests/test_visual.py-snapshots/` to git —
   it's the "expected" image every future run is diffed against.
4. Every subsequent run compares the live page render to that baseline.

**Pitfalls (read this before you rely on visual tests):**

- **Font rendering differs by OS.** Windows, macOS, and Linux render the
  same font with different anti-aliasing and hinting. A baseline captured
  on a developer's Windows laptop **will** mismatch when compared against a
  Linux-based CI runner, producing a false "regression" on every run.
- **Minor browser/OS version bumps** can shift sub-pixel rendering enough
  to trip a tight tolerance.
- **Dynamic content** (timestamps, ads, carousels, animations) needs to be
  masked (`mask=[locator]`) or frozen/disabled, or the test will "regress"
  every time that content changes — which is most of the time.

**The fix: generate and run visual tests in one consistent environment —
Docker, and the *same* Docker image, both locally and in CI.** This repo's
[`Dockerfile`](Dockerfile) is built on the official Playwright image
specifically so that whoever generates baselines (a developer running the
container locally) and whoever verifies them (CI) are rendering pixels
identically. Never compare a locally-captured baseline against a
CI-rendered screenshot, or vice versa — that mismatch is the #1 cause of
"flaky" visual tests, and it isn't flakiness, it's an environment mismatch.

```bash
# Generate/refresh baselines inside the same environment CI uses:
docker build -t playwright-tutorial-05 .
docker run --rm -v "$(pwd)/tests:/app/tests" playwright-tutorial-05 \
  pytest tests/test_visual.py --update-snapshots
```

---

## Multi-Browser & Device Emulation

Playwright ships Chromium, Firefox, and WebKit (Safari's engine) as part of
the library itself — no separate driver binaries to download and
version-match, which is a manual, brittle chore in Selenium. Run the same
suite against all three:

```bash
pytest --browser chromium
pytest --browser firefox
pytest --browser webkit

# or all three in one invocation:
pytest --browser chromium --browser firefox --browser webkit
```

**Device emulation** goes further: Playwright ships a catalog of real
device profiles (viewport size, user agent, touch support, device scale
factor) for mobile responsive testing, with no physical device or emulator
required.

```python
# In a conftest.py or directly in a test file
import pytest

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright):
    iphone_13 = playwright.devices["iPhone 13"]
    return {**browser_context_args, **iphone_13}
```

Or per-test, without changing the global fixture:

```python
def test_mobile_login_layout(playwright, browser):
    iphone_13 = playwright.devices["iPhone 13"]
    context = browser.new_context(**iphone_13)
    page = context.new_page()
    page.goto("https://www.saucedemo.com/")
    # ... assertions against the mobile layout
    context.close()
```

This is genuinely hard to do well in Selenium (typically requires a real
device farm or a separately configured mobile emulator per browser);
Playwright bakes it into `new_context()`.

---

## Parallelization & Sharding

Two different techniques, solving two different problems — production
suites usually use **both**, together.

### Workers (`pytest-xdist`, one machine)

```bash
pytest -n auto
```

`pytest-xdist`'s `-n auto` spins up one worker process per CPU core on the
**current machine** and distributes test *functions* across them. This
speeds up a run on a single box (your laptop, or a single CI runner) by
using all available cores instead of running tests serially. It doesn't
help once you've saturated one machine's cores — for that, you need
sharding.

### Shards (Playwright's `--shard`, multiple machines)

```bash
# Split the suite into 3 groups, run group 1 of 3:
pytest --shard=1/3
pytest --shard=2/3
pytest --shard=3/3
```

`--shard=<i>/<n>` splits the **whole test suite** into `n` disjoint groups
and runs only group `i`. Unlike workers, each shard is meant to run on a
**separate CI machine/job in parallel** — this is how you scale a suite
horizontally past a single machine's core count. A CI matrix job (e.g.
GitHub Actions `strategy.matrix`) typically runs each shard as its own
job, and each of those jobs can *also* use `-n auto` internally.

**The distinction that matters:** workers parallelize *within* one
machine's process pool; shards parallelize *across* separate machines/CI
jobs. A CI setup with 3 shard jobs, each running `-n auto` on a 4-core
runner, gets you up to 12-way parallelism total — 3x from sharding, 4x
from workers within each shard.

```yaml
# Example: a 3-way sharded matrix in GitHub Actions
strategy:
  matrix:
    shard: [1, 2, 3]
steps:
  - run: pytest -n auto --shard=${{ matrix.shard }}/3
```

---

## Dockerizing Playwright Tests

The official `mcr.microsoft.com/playwright/python` image ships Python,
Playwright, and every browser + OS-level dependency (fonts, codecs, etc.)
already installed and version-matched to the Playwright release. This
eliminates an entire class of "works on my machine, fails in CI" bugs
caused by mismatched system libraries — and, as covered above, it's also
what keeps visual-regression baselines reproducible across machines.

See [`Dockerfile`](Dockerfile) in this directory:

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# No `playwright install --with-deps` needed -- baked into the base image.
COPY . .
CMD ["pytest", "-n", "auto", "--tracing=retain-on-failure", "--html=report.html", "--self-contained-html"]
```

Build and run:

```bash
docker build -t playwright-tutorial-05 .
docker run --rm --env-file .env playwright-tutorial-05
```

Note the image tag (`v1.47.0-jammy`) is pinned to match the `playwright`
version in [`requirements.txt`](requirements.txt). A mismatched image/pip
version pair is a common source of confusing "executable doesn't exist"
errors — always keep them in lockstep.

---

## CI/CD with GitHub Actions

[`.github/workflows/playwright-ci.yml`](.github/workflows/playwright-ci.yml)
runs the suite on every push/PR to `main`, using the same official
Playwright Docker image as a job container (so CI renders identically to
local Docker runs), then:

1. Installs dependencies and confirms browsers are present
   (`playwright install --with-deps` — a fast no-op when the base image
   already has them, a safety net if `requirements.txt` ever drifts ahead
   of the image).
2. Runs the suite in parallel with tracing enabled only for failures:

   ```bash
   pytest -n auto --tracing=retain-on-failure --html=report.html --self-contained-html
   ```

3. Uploads the HTML report **every run** (`if: always()`), so you can see
   results even on green builds.
4. Uploads trace files **only on failure** (`if: failure()`), since
   `--tracing=retain-on-failure` means passing tests produce no trace at
   all — nothing to upload, no wasted artifact storage.

Download a failure trace from the Actions run's "Artifacts" section and
open it with:

```bash
playwright show-trace trace.zip
```

See the [Trace Viewer](#debugging-with-the-trace-viewer-deep-dive) section
below for what to actually look for once it's open.

---

## Test Data & Environment Config via `.env`

Mirrors the pattern from
[Tutorial 3](../03-selenium-advanced-production-patterns/README.md) so
config handling is consistent across the whole series: **never hardcode
URLs or credentials in test code.**

[`.env.example`](.env.example):

```
BASE_URL=https://www.saucedemo.com
SAUCE_USERNAME=standard_user
SAUCE_PASSWORD=secret_sauce
```

Copy it to `.env` (gitignored) and adjust as needed. [`conftest.py`](conftest.py)
and [`auth_setup/generate_auth_state.py`](auth_setup/generate_auth_state.py)
both load it via `python-dotenv`'s `load_dotenv()` and read values with
`os.getenv(...)`, with sane fallbacks so the suite still runs against the
public demo credentials if no `.env` is present.

In CI, `.env` doesn't exist at all — instead, the same variable names are
injected as job environment variables sourced from GitHub Actions Secrets
(see the `env:` block in the workflow file). The application code and test
code never know or care whether a value came from a local `.env` file or a
CI secret store — that's the point of routing everything through
`os.getenv()`.

---

## Debugging with the Trace Viewer (Deep Dive)

Tutorial 4 introduced `--tracing=on`. Here's how to actually use a trace to
solve the hardest class of bug: **a failure that only happens in CI and
won't reproduce locally.**

Generate a trace for a specific run:

```bash
pytest --tracing=retain-on-failure
playwright show-trace test-results/<test-name>/trace.zip
```

Once open, the Trace Viewer gives you a **timeline scrubber across every
action the test took**, and for each action, four synchronized panels:

- **DOM snapshot at that exact moment** — not a screenshot, an actual
  interactive snapshot of the page's DOM/CSS at that point in time. You can
  inspect elements, check computed styles, and see *exactly* what the test
  saw when it clicked/typed/asserted — this alone resolves most
  "element not found" or "assertion failed on wrong text" CI mysteries,
  because you're looking at the real state, not guessing from a log line.
- **Network tab** — every request the page made during that action, with
  status codes, timing, and payloads. A CI-only failure caused by a slow or
  failing third-party call, a race between a fetch and a UI update, or a
  request that behaves differently under CI's network conditions shows up
  here directly.
- **Console tab** — JavaScript console output and errors. A CI-only crash
  in application code (that happens to not throw locally, e.g. due to a
  timing difference) is often sitting in here as an uncaught exception.
- **Action log / call panel** — the exact Playwright API calls made, their
  parameters, and how long each took, including auto-wait time. If an
  action "waited" much longer in CI than locally, that's visible here as a
  clue toward a timing-dependent bug.

**Workflow for a CI-only failure:**

1. Pull the `trace.zip` artifact from the failed CI run (uploaded by the
   workflow's "Upload failure traces" step).
2. Open it and scrub to the failing action.
3. Check the DOM snapshot first — is the element actually there, just not
   where/what the locator expected? (Common cause: CI runs headless at a
   different default viewport than your local headed run.)
4. Check the network tab — did a request that's fast/reliable locally
   respond slowly or differently in CI? (Common cause: CI egress network
   characteristics, or a third-party dependency behaving differently.)
5. Check the console tab for errors that wouldn't show up in pytest's
   output at all, since they're inside the browser, not the test process.

This is the single biggest reason Playwright suites are easier to maintain
at scale than Selenium suites: Selenium gives you a stack trace from the
test process. Playwright's trace gives you a complete, scrubbable replay
of everything the browser did.

---

## Production Best Practices Checklist

- [ ] **Reuse authentication state** (`storage_state`) instead of logging
      in through the UI in every test.
- [ ] **Mock flaky or unrelated third-party APIs** with `page.route()`
      rather than depending on them being up during your test run.
- [ ] **Run visual regression tests in one consistent environment**
      (Docker, same image locally and in CI) — never compare baselines
      across different OS/browser render environments.
- [ ] **Shard for CI speed** once a suite outgrows a single machine's
      cores, and use `-n auto` workers *within* each shard.
- [ ] **Capture traces only on failure** (`--tracing=retain-on-failure`)
      to keep CI artifact storage small — you don't need a trace for a
      test that passed.
- [ ] **Isolate tests meaningfully**: each test should set up its own
      state (via API calls or `storage_state`, not shared mutable fixtures)
      so tests can run in any order, in parallel, without interfering with
      each other.
- [ ] **No hardcoded secrets** — route everything through `.env` locally
      and CI secrets in pipelines.
- [ ] **CI integration from day one** — a test suite that only runs on one
      person's laptop isn't a safety net for the team.

---

## What's Next

You now have a suite that mocks unreliable dependencies, skips redundant
login flows, catches visual regressions, runs across browsers and devices,
scales horizontally in CI, and gives you a full replay of any failure. The
remaining gap: all of this is still triggered and interpreted by a human.

[Tutorial 6](../06-ai-agent-automation-mcp-claude-code/README.md) covers
wiring this kind of suite into AI agent workflows — using MCP
(Model Context Protocol) and Claude Code to let an AI agent run tests,
read trace output, and iterate on failures as part of an automated
development loop.
