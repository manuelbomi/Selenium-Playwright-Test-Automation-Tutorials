# Worked Example: Self-Healing a Broken Locator

This walks through one concrete "self-healing" cycle end to end: a UI
change breaks a locator, a test fails, we prompt Claude Code to diagnose
and fix it, and we review the resulting diff before merging. Nothing here
merges itself — the agent proposes a change, a human approves it.

## 1. The setup: a Page Object with a brittle locator

`05-playwright-advanced-production-patterns/pages/checkout_page.py`
(before):

```python
from playwright.sync_api import Page


class CheckoutPage:
    def __init__(self, page: Page):
        self.page = page
        self.checkout_button = page.locator("#old-checkout-btn")
        self.first_name_input = page.locator("#first-name")
        self.last_name_input = page.locator("#last-name")
        self.postal_code_input = page.locator("#postal-code")

    def start_checkout(self):
        self.checkout_button.click()

    def fill_shipping_info(self, first_name: str, last_name: str, postal_code: str):
        self.first_name_input.fill(first_name)
        self.last_name_input.fill(last_name)
        self.postal_code_input.fill(postal_code)
```

`#old-checkout-btn` was the button's `id` when this Page Object was
written. A recent front-end change (a checkout redesign) dropped that
`id` attribute from the markup, though the button's visible text and role
are unchanged.

## 2. The failure

Running the suite produces a timeout, not an assertion failure — the
locator never resolves to an element:

```
$ pytest -q tests/test_checkout.py

tests/test_checkout.py::test_checkout_flow FAILED

________________________ test_checkout_flow _________________________

    def test_checkout_flow(authenticated_page):
        cart_page = CartPage(authenticated_page)
        checkout_page = CheckoutPage(authenticated_page)
        cart_page.go_to_cart()
>       checkout_page.start_checkout()

pages/checkout_page.py:13: in start_checkout
    self.checkout_button.click()
E   playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E   Call log:
E     - waiting for locator("#old-checkout-btn")
E     -   locator resolved to 0 elements

1 failed in 5.42s
```

This is exactly the failure signature of a locator that no longer matches
anything in the DOM — worth recognizing on sight before reaching for an
agent at all, but it's also a good case to hand off because confirming
the *new* markup requires either reading updated frontend code or looking
at the live page.

## 3. The prompt given to the agent

Using the Playwright MCP server (connected per the main `README.md`) so
the agent can inspect the live staging page rather than guess:

```
The locator in pages/checkout_page.py
(page.locator("#old-checkout-btn")) is failing with a timeout — see the
pytest output above. Use the Playwright MCP tools to navigate to the
staging cart page, log in with the test account from .env, and take an
accessibility snapshot of the checkout button. Find its current
accessible role and name, then update CheckoutPage to use
page.get_by_role(...) instead of the id selector. Run
tests/test_checkout.py afterward to confirm it passes, and show me the
diff — don't commit it.
```

The agent navigates the live page via the MCP tools, reads the
accessibility snapshot, and finds that the button now renders as:

```html
<button class="btn_action checkout_button_v2">Checkout</button>
```

with no `id`, but with an accessible role of `button` and accessible name
`"Checkout"` — unchanged from before the redesign, because visible text
didn't change even though the `id` and CSS classes did.

## 4. The corrected code

`pages/checkout_page.py` (after):

```python
from playwright.sync_api import Page


class CheckoutPage:
    def __init__(self, page: Page):
        self.page = page
        self.checkout_button = page.get_by_role("button", name="Checkout")
        self.first_name_input = page.get_by_label("First Name")
        self.last_name_input = page.get_by_label("Last Name")
        self.postal_code_input = page.get_by_label("Postal Code")

    def start_checkout(self):
        self.checkout_button.click()

    def fill_shipping_info(self, first_name: str, last_name: str, postal_code: str):
        self.first_name_input.fill(first_name)
        self.last_name_input.fill(last_name)
        self.postal_code_input.fill(postal_code)
```

(The agent also swapped the shipping-form `id` locators for
`get_by_label`, since it noticed the same redesign moved those fields to
generated ids too — flagged in its summary for review rather than done
silently.)

```
$ pytest -q tests/test_checkout.py
1 passed in 1.87s
```

## Why this locator is more resilient

`page.get_by_role("button", name="Checkout")` targets the button's
**accessible role and name** — the same contract screen readers rely on —
rather than an implementation detail like an `id` or CSS class that a
front-end redesign can change without changing what the button *is* or
*does*. This is the same guidance from Tutorial 4
(`../04-playwright-fundamentals/README.md`): prefer role/label/text-based
locators over selectors tied to styling or generated markup, because they
break only when the user-facing behavior actually changes — which is
exactly when you *want* a test to fail.

## What still needs a human

The agent's diff is a proposal, not a merge. Before approving it, a
reviewer should confirm:

- The new locator is unambiguous (only one "Checkout" button on the
  page).
- The unrelated `get_by_label` change for the shipping fields is correct
  and in scope — or split into a separate, reviewed change if not.
- No credentials or staging URLs were hardcoded into the test as a side
  effect of the live exploration.
