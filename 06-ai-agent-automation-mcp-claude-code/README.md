# Tutorial 6: AI-Driven Test Automation — Using Claude Code & MCP Agents with Selenium and Playwright

This is the final tutorial in the *Selenium & Playwright Test Automation
Tutorials* series. Tutorials 1–5 built a real Python automation framework:
environment setup, Selenium fundamentals, advanced/production Selenium (Page
Object Model at scale, parallelization, Docker Grid, CI), Playwright
fundamentals, and advanced/production Playwright (network mocking,
`storage_state` auth reuse, visual testing, sharding, Docker/CI).

This tutorial doesn't add new test framework features. It teaches how to use
an AI coding agent — specifically **Claude Code** — together with the **Model
Context Protocol (MCP)** to write, run, debug, and maintain the Selenium and
Playwright suite you already have, faster, while keeping a human in charge of
what actually merges.

## Table of contents

- [What is MCP?](#what-is-mcp)
- [What is Claude Code, and how does it fit in?](#what-is-claude-code-and-how-does-it-fit-in)
- [Two distinct patterns for combining AI with this suite](#two-distinct-patterns-for-combining-ai-with-this-suite)
  - [Pattern A: Agent-authored test code](#pattern-a-agent-authored-test-code)
  - [Pattern B: Agent-driven live browsing via the Playwright MCP server](#pattern-b-agent-driven-live-browsing-via-the-playwright-mcp-server)
- [Installing and configuring the Playwright MCP server](#installing-and-configuring-the-playwright-mcp-server)
- [CLAUDE.md: project conventions the agent follows](#claudemd-project-conventions-the-agent-follows)
- [Prompt library](#prompt-library)
- [Worked example: before/after selector healing](#worked-example-beforeafter-selector-healing)
- [Guardrails: using agents safely in a test automation context](#guardrails-using-agents-safely-in-a-test-automation-context)
- [A conceptual CI pattern for AI-assisted maintenance](#a-conceptual-ci-pattern-for-ai-assisted-maintenance)
- [Series recap and next steps](#series-recap-and-next-steps)

---

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard for connecting AI
agents to external tools and data sources through a common interface. Instead
of every AI application needing a custom, bespoke integration for every tool
it wants to use (one integration for a browser, another for a database,
another for a ticketing system), a tool exposes itself once as an **MCP
server**, and any MCP-compatible agent (an **MCP client**) can discover and
call that server's tools the same way. An MCP server can expose "tools" (
actions the agent can call, like "navigate to a URL" or "click an element"),
as well as data resources and prompt templates. For test automation, the
practical effect is that an agent like Claude Code can be handed a new
capability — such as controlling a real browser — by connecting it to an MCP
server, without Anthropic or anyone else having to build that integration
into the agent itself.

## What is Claude Code, and how does it fit in?

**Claude Code** is Anthropic's agentic command-line coding tool. Run inside a
project directory, it can:

- Read and edit files in your repo (Page Objects, test files, fixtures,
  config).
- Run shell commands — including `pytest`, `npm`, `playwright install`, `git`
  — and read their output.
- Connect to **MCP servers** and call their tools as part of its normal
  workflow, alongside its file and shell tools.

In this project, that means Claude Code can do everything a human contributor
does at a terminal — read the existing Page Object Model, write a new test,
run the suite, read the failure output, and propose a fix — and, when an MCP
server like `@playwright/mcp` is connected, it can additionally drive a real
browser directly as one more tool in its toolbox. Nothing about MCP or Claude
Code bypasses your normal engineering process: the agent produces diffs and
command output for you to read, the same as any other contributor.

## Two distinct patterns for combining AI with this suite

It's easy to blur these together, so this tutorial keeps them explicitly
separate. They use different tools and solve different problems.

### Pattern A: Agent-authored test code

**What it is:** you ask Claude Code to write or extend the actual Pytest /
Selenium / Playwright test files that live in this repo — no MCP server
required, just Claude Code's normal file and shell tools.

**Example prompt:**

```
Add a Playwright test for the checkout flow in
05-playwright-advanced-production-patterns/tests/, covering the
acceptance criterion: "a logged-in user can add an item to the cart and
complete checkout." Read the existing Page Objects and conftest.py first
and follow the same conventions. Run pytest yourself and fix any
failures before showing me the diff.
```

**What happens:** the agent reads `pages/`, `tests/`, and `conftest.py` in
that folder to learn the existing Page Object Model and fixture
conventions, writes or edits the test file(s), and runs `pytest` itself to
verify the test passes *before* you ever see it. You then review the diff
like any other pull request.

This is the pattern you'll use for most day-to-day work: new tests,
converting a manual test case, extending an existing suite, fixing a locator
you already know the correct value for.

### Pattern B: Agent-driven live browsing via the Playwright MCP server

**What it is:** the official Playwright MCP server (**`@playwright/mcp`** on
npm, published by Microsoft) exposes browser automation as tools an agent can
call directly — navigate, click, type, take an accessibility-tree snapshot,
and so on. When this server is connected to Claude Code, the agent can drive
a **real, live browser** step by step, the same way a human exploring an
unfamiliar app would.

This is explicitly **not** the same thing as writing Playwright test code. In
Pattern A, the agent edits `.py` files containing Playwright API calls that
*will run later, as a test*. In Pattern B, the agent itself is the one
issuing the browser actions, right now, through MCP tool calls, to look at
and interact with a page — there's no test file involved unless the agent (or
you) subsequently writes one based on what it found.

**Example prompt:**

```
Using the Playwright MCP tools, navigate to https://www.saucedemo.com,
log in as standard_user / secret_sauce, and walk through the add-to-cart
and checkout flow. Take an accessibility snapshot at each step and report
back the role and accessible name of each key button, so I can review it
before we turn it into a Page Object.
```

**What happens:** the agent calls MCP tools like "navigate," "click," and
"snapshot" to actually control a browser instance, reads back the
accessibility tree it gets from each snapshot, and reports what it found in
plain text (or proposes a code change). This is ideal for exploring an
unfamiliar app, discovering the correct selector for something, or
reproducing a bug interactively — then you (or the agent, in a follow-up
step you review) translate what was learned into a committed Page Object
change.

**In short:** Pattern A is "the agent edits code that automates a browser."
Pattern B is "the agent *is* driving a browser, live, via tool calls, right
now." They compose well together — explore live via MCP, then commit what
you learned as ordinary Page Object code — but they are not the same
capability, and this tutorial uses them for different jobs throughout.

---

## Installing and configuring the Playwright MCP server

The Playwright MCP server is a Node package (`@playwright/mcp`), run via
`npx`, so it needs Node.js installed (already a prerequisite from the
Playwright tutorials) but no separate global install is required.

### Option 1: `claude mcp add` (CLI)

From the repo root, register the server with Claude Code:

```bash
claude mcp add playwright npx @playwright/mcp@latest
```

This registers an MCP server named `playwright` that Claude Code will start
(via `npx @playwright/mcp@latest`) whenever it needs it.

### Option 2: project-scoped `.mcp.json`

Equivalently, check a `.mcp.json` file into the project so every contributor
(and CI) gets the same MCP server configuration automatically. This
tutorial's folder includes one — see
[`.mcp.json`](./.mcp.json):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

Checking this in (rather than only registering it locally with `claude mcp
add`) means the whole team gets the same MCP tool available without each
person configuring it by hand — the same reasoning as checking in a
`requirements.txt` or `package.json`.

> **Note on versioning:** `@playwright/mcp@latest` is convenient for a
> tutorial, but for a real project pin an exact version (e.g.
> `@playwright/mcp@0.x.y`) the same way you'd pin any other dependency — see
> [Guardrails](#guardrails-using-agents-safely-in-a-test-automation-context)
> below.

### Verifying it's connected

Two ways to confirm the server is registered and reachable:

- From the shell: `claude mcp list` — this lists configured MCP servers and
  their connection status.
- From inside a Claude Code session: run `/mcp` — this shows connected MCP
  servers and the tools they expose (for `@playwright/mcp`, tools like
  browser navigation, clicking, typing, and taking accessibility
  snapshots).

If the server doesn't show as connected, confirm Node/`npx` is on your
`PATH` and that `.mcp.json` is valid JSON (a trailing comma or similar typo
will silently break it).

---

## CLAUDE.md: project conventions the agent follows

Claude Code automatically reads a `CLAUDE.md` file at the root of a project
at the start of a session. It's where you put the conventions you'd
otherwise repeat in every prompt: where Page Objects live, how tests are
named, that the relevant subfolder's `pytest` must be run before a task is
considered done, that `.env` and `state.json` must never be committed, and
that `time.sleep()` is not an acceptable substitute for explicit/auto-waits.

This tutorial's [`CLAUDE.md`](./CLAUDE.md) is written as a real example you
can copy into your own repo (adjusting the paths for your project layout).
It is intentionally short and directive — it's read by the agent, not a
person browsing documentation, so it favors concrete rules ("tests live
under `tests/`, named `test_<feature>.py`") over prose explanation.

---

## Prompt library

[`prompts/prompt-library.md`](./prompts/prompt-library.md) contains ten
concrete, copy-pasteable prompts grouped by workflow:

- **Generating new tests** — from a plain-English acceptance criterion.
- **Converting manual test cases** — turning a written manual test case into
  automated Playwright or Selenium code.
- **Debugging failures** — having the agent read the `pytest-html` report or
  a Playwright trace and propose a fix grounded in the actual failure, not a
  guess.
- **Self-healing broken selectors** — both a static diagnosis (from error
  output and repo code alone) and a live one (using the Playwright MCP
  server to inspect the current page and find the new selector).
- **Exploring an app via MCP** — using Pattern B to map out an unfamiliar
  flow or reproduce a bug before writing any test code.

Every prompt is written the way you'd actually type it, referencing real
files and patterns from this series (`saucedemo.com`, the Page Object
pattern from Tutorials 4/5, `conftest.py` fixtures, `pytest-html` reports).

---

## Worked example: before/after selector healing

To make "self-healing" concrete rather than abstract,
[`examples/before_after_selector_healing.md`](./examples/before_after_selector_healing.md)
walks through one full cycle:

1. A `CheckoutPage` object with `page.locator("#old-checkout-btn")` — a
   locator tied to an `id` that a UI redesign removed.
2. The resulting `pytest` failure output (a `TimeoutError`, because the
   locator resolves to zero elements).
3. The exact prompt given to Claude Code (using the Playwright MCP server to
   inspect the live page and find the button's current accessible role and
   name).
4. The corrected code: `page.get_by_role("button", name="Checkout")`.
5. A one-line explanation of why the new locator is more resilient — it
   targets the button's accessible role and name rather than an
   implementation detail like an `id`, consistent with the locator guidance
   from
   [Tutorial 4](../04-playwright-fundamentals/README.md).

It also spells out what a human reviewer should still check before merging
that kind of change (locator uniqueness, no hardcoded credentials picked up
during live exploration, scope of the diff).

---

## Guardrails: using agents safely in a test automation context

An agent that can run shell commands and, via MCP, drive a real browser is
powerful — treat it with the same caution you'd apply to any automation with
broad access, adjusted for a few risks specific to this context:

- **Never point an agent at a production environment.** Whether the agent is
  running tests (Pattern A) or driving a live browser via MCP (Pattern B), it
  should only ever target test/staging environments, using test-only
  accounts. Configure base URLs and credentials via `.env` (gitignored, per
  `CLAUDE.md`) and never let a prompt or MCP session point at a production
  URL, even "just to check something."
- **Always require human review of agent-written code.** Agent-authored
  tests and fixes go through the exact same pull-request review your team
  already uses — no auto-merge, no exception for "the agent already ran the
  tests and they passed." Passing tests confirm the code runs; they don't
  confirm it's testing the right thing, or that a "fix" didn't quietly
  loosen an assertion.
- **Be careful about how much shell access an agent has in CI.** Running
  `claude -p` non-interactively in a pipeline (see the next section) means
  giving it access to a shell in an environment that likely also has repo
  write access and secrets. Scope what it's allowed to run, keep CI
  permissions minimal (`contents: write` and `pull-requests: write` at most
  for a maintenance job — not admin or deploy permissions), and never let an
  automated agent run push directly to a protected branch.
- **Treat MCP servers like any other third-party dependency.** `@playwright/mcp`
  runs code on your machine (or CI runner) and can control a real browser,
  including whatever session/cookies exist in that browser context. Pin a
  specific version rather than `@latest` in anything beyond a tutorial,
  review what data and tools any MCP server you add actually exposes before
  connecting it, and don't add MCP servers to a shared `.mcp.json` casually —
  it's a dependency the whole team picks up.

---

## A conceptual CI pattern for AI-assisted maintenance

[`.github/workflows/ai-assisted-test-maintenance.yml`](./.github/workflows/ai-assisted-test-maintenance.yml)
sketches a workflow that:

1. Triggers manually (`workflow_dispatch`) or on a schedule.
2. Checks out the repo, installs Python/Playwright dependencies and the
   Claude Code CLI.
3. Runs the target test suite and captures whether anything failed.
4. If something failed, runs Claude Code **non-interactively** —
   `claude -p "<prompt>"` (Claude Code's print/non-interactive mode, meant
   for exactly this kind of scripted/CI use) — with a prompt instructing it
   to read the failure report, distinguish a broken selector from a real
   application bug, fix only the selector case, and re-run the suite to
   confirm.
5. Opens a **pull request** with the proposed change via
   `peter-evans/create-pull-request`, labeled `ai-generated` and
   `needs-human-review` — it never pushes to `main` directly.

This workflow is explicitly **illustrative** — a starting point, not a
drop-in solution. Before using anything like it for real, your team should
adapt:

- **Auth**: where `ANTHROPIC_API_KEY` and test-environment credentials come
  from (repo/org secrets, with spend limits on the API key), and whether an
  environment protection rule should gate the job.
- **Permissions**: the workflow requests the minimum GitHub permissions it
  needs (`contents: write`, `pull-requests: write`) — review this against
  your org's policies rather than assuming it's already minimal enough.
- **Cost controls**: non-interactive agent runs in CI consume API usage on
  every scheduled run; a spend cap on the key and a narrow, specific prompt
  (as shown) both help keep this predictable.
- **Scope**: the example prompt explicitly tells the agent not to touch
  anything outside the target suite folder and not to "fix" a real
  application bug by loosening a test assertion — keep guardrails like this
  in any prompt you run unattended.

---

## Series recap and next steps

This tutorial series took you from zero to an AI-assisted, production-style
Selenium + Playwright automation framework in Python:

1. [**Foundations & Environment Setup**](../01-foundations-and-environment-setup/) —
   Python, virtual environments, installing Selenium and Playwright, editor
   setup.
2. [**Selenium Fundamentals**](../02-selenium-fundamentals/) — WebDriver
   basics, locators, waits, and an initial Page Object Model.
3. [**Selenium Advanced/Production Patterns**](../03-selenium-advanced-production-patterns/) —
   Page Object Model at scale, parallel test execution, a Dockerized Selenium
   Grid, and CI integration.
4. [**Playwright Fundamentals**](../04-playwright-fundamentals/) —
   Playwright's API, auto-waiting, and the Page Object Model in Playwright.
5. [**Playwright Advanced/Production Patterns**](../05-playwright-advanced-production-patterns/) —
   network mocking, `storage_state` for reusable auth, visual regression
   testing, test sharding, and Docker/CI.
6. **AI-Driven Test Automation** *(this tutorial)* — using Claude Code and
   the Playwright MCP server to author tests, debug failures, and self-heal
   broken selectors, with human review as a constant.

### Suggested next steps

- **Allure reporting** — richer, historical test reporting than
  `pytest-html`, useful once you're running this suite regularly in CI and
  want trend data across runs.
- **BDD with `pytest-bdd`** — writing acceptance criteria as Gherkin
  `Given/When/Then` scenarios that map to the same Page Objects built in
  Tutorials 2–5; pairs naturally with the "acceptance criterion → test"
  prompts in this tutorial's [prompt library](./prompts/prompt-library.md).
- **Full test pyramid strategy** — this series focused on UI/E2E automation;
  a mature suite balances that with unit and API/integration tests so the
  slower, more brittle UI layer isn't carrying more coverage weight than it
  should.
