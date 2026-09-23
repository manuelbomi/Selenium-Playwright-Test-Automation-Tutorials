# Selenium & Playwright Test Automation Tutorials

A six-part, hands-on tutorial series on browser test automation with **Selenium** and **Playwright** in Python — from first principles to production-grade frameworks to AI-agent-assisted test authoring with **Claude Code** and **MCP**.

Every tutorial is self-contained: its own `README.md`, its own `requirements.txt`, and real, runnable code. All hands-on exercises run against public demo sites ([saucedemo.com](https://www.saucedemo.com/) and [the-internet.herokuapp.com](https://the-internet.herokuapp.com/)) so you can clone this repo and run every test immediately — no app of your own required.

Written for junior engineers who know basic Python but are new to browser automation, and detailed enough to serve as a production reference.

## Who this is for

You should be comfortable with basic Python (functions, classes, imports) and the command line. No prior Selenium, Playwright, or test-automation experience is assumed.

## Series contents

| # | Tutorial | What you'll learn |
|---|---|---|
| 1 | [Test Automation Foundations: Selenium vs. Playwright & VS Code Environment Setup](01-foundations-and-environment-setup/README.md) | What Selenium and Playwright are, how their architectures differ, when to pick which, and a full VS Code + Python environment setup with a "Hello World" for both frameworks |
| 2 | [Selenium WebDriver Fundamentals: Locators, Waits & Your First Test Suite](02-selenium-fundamentals/README.md) | Locator strategies, explicit vs. implicit waits, the Page Object Model, pytest fixtures, and a real login/cart test suite |
| 3 | [Advanced Selenium: Page Object Model at Scale, Parallel Execution & CI/CD](03-selenium-advanced-production-patterns/README.md) | iframes/alerts/windows/uploads, cross-browser testing, config & secrets management, parallel execution, Dockerized Selenium Grid, and GitHub Actions CI |
| 4 | [Playwright Fundamentals: Setup, Locators & Auto-Waiting Explained](04-playwright-fundamentals/README.md) | Browser/Context/Page architecture, accessibility-first locators, auto-waiting, `expect()` assertions, codegen, and the Trace Viewer — the same exercises as Tutorial 2, for direct comparison |
| 5 | [Advanced Playwright: Network Interception, Visual Testing, Parallelization & CI/CD](05-playwright-advanced-production-patterns/README.md) | API mocking, auth-state reuse, visual regression, device emulation, sharding, Docker, and CI/CD |
| 6 | [AI-Driven Test Automation: Using Claude Code & MCP Agents with Selenium and Playwright](06-ai-agent-automation-mcp-claude-code/README.md) | The Model Context Protocol, the Playwright MCP server, agent-assisted test authoring and "self-healing" locators, and safe agentic CI patterns |

Tutorials 1→3 cover Selenium end to end; 1, 4→5 cover Playwright end to end; Tutorial 6 applies to both. Read the whole series in order, or jump to whichever track you need.

## Quick start

Each tutorial folder is independently runnable:

```bash
cd 02-selenium-fundamentals   # or any other tutorial folder
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
playwright install            # only needed in the Playwright tutorials (1, 4, 5)

pytest -v
```

See [Tutorial 1](01-foundations-and-environment-setup/README.md) for the full environment setup walkthrough, including VS Code configuration.

## Repository structure

```
Selenium-Playwright-Test-Automation-Tutorials/
├── 01-foundations-and-environment-setup/
├── 02-selenium-fundamentals/
├── 03-selenium-advanced-production-patterns/
├── 04-playwright-fundamentals/
├── 05-playwright-advanced-production-patterns/
└── 06-ai-agent-automation-mcp-claude-code/
```

## License

[MIT](LICENSE) — use this code freely in your own projects and tutorials.
