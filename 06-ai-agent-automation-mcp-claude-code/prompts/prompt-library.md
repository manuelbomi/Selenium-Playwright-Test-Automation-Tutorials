# Prompt Library — AI-Assisted Test Automation Workflows

Copy-pasteable prompts for common workflows in this repo. Run these with
Claude Code in the repo root (or the relevant tutorial subfolder) so the
agent has file access via its normal read/edit/shell tools. Prompts that need
live-browser exploration call out that the `playwright` MCP server (from
`.mcp.json`) must be connected — see the main `README.md` for setup.

Every prompt below produces a **diff for you to review**, not a merged
change. Treat agent output the same way you'd treat a pull request from a
junior teammate: read it before it ships.

---

## Generating new tests

### 1. New test from a plain-English acceptance criterion

```
In 05-playwright-advanced-production-patterns/, add a new Playwright test
for this acceptance criterion:

"A logged-in user on saucedemo.com can add two items to the cart, proceed
to checkout, fill in first name / last name / postal code, and see an order
confirmation message on the finish page."

Read the existing Page Objects under pages/ and the fixtures in
conftest.py (including the storage_state-based authenticated_page fixture
from Tutorial 5) first, and follow the same patterns — do not invent a new
fixture style. Add the test to tests/test_checkout.py, creating the file if
it does not exist. Use role/label-based locators, not raw CSS selectors.
Run `pytest -q tests/test_checkout.py` yourself and fix any failures before
you show me the diff.
```

### 2. New test with a data-driven variation

```
Extend 02-selenium-fundamentals/tests/test_login.py to cover three login
cases as parametrized tests: valid user, locked_out_user, and an invalid
password. Reuse the LoginPage object under pages/ — do not add new
selectors to the test file itself. Run pytest for that file and paste the
result in your summary.
```

---

## Converting manual test cases

### 3. Manual test case to automated Playwright code

```
Here is a manual test case from our test plan:

  Title: Remove item from cart updates item count
  Steps:
    1. Log in as standard_user on saucedemo.com
    2. Add "Sauce Labs Backpack" to the cart
    3. Open the cart page
    4. Click "Remove" next to the item
    5. Verify the cart badge disappears and the cart page shows no items

Convert this into an automated Playwright test in
05-playwright-advanced-production-patterns/tests/test_cart.py, using the
existing CartPage object (or extending it if the remove action isn't there
yet) under pages/. Follow the Page Object conventions from CLAUDE.md. Run
the test and confirm it passes before showing me the diff.
```

### 4. Manual test case to Selenium code with explicit waits

```
Convert this manual regression case into a Selenium test under
03-selenium-advanced-production-patterns/tests/:

  Title: Sort products by price, low to high
  Steps:
    1. Log in as standard_user
    2. On the inventory page, select "Price (low to high)" from the sort
       dropdown
    3. Verify the product list is sorted ascending by price

Use WebDriverWait with expected_conditions for synchronization — no
time.sleep(). Add any new locators to the existing InventoryPage object
rather than inlining them in the test.
```

---

## Debugging failures

### 5. Diagnose a failure from the pytest-html report

```
The last run of 05-playwright-advanced-production-patterns produced a
pytest-html report at report.html and a trace at
test-results/test_checkout/trace.zip because test_checkout_flow failed.
Read the report and the trace (open it with `playwright show-trace` if
needed, or summarize what you can from the trace's network/console logs),
identify the root cause of the failure, and propose a fix. Do not change
the test's expected behavior to make it pass — if the assertion is
correct and the app changed, fix the Page Object; if the test itself is
wrong, explain why before changing it.
```

### 6. Diagnose a flaky test

```
tests/test_search.py::test_search_returns_results has failed intermittently
in CI over the last week (see the linked run logs). Run it 10 times locally
with `pytest tests/test_search.py -k test_search_returns_results --count=10`
(or a loop if pytest-repeat isn't installed) and tell me whether it's a
timing/synchronization issue, a test-order/state-leak issue, or an actual
app bug. Propose the minimal fix — prefer a proper wait condition over
increasing a timeout.
```

---

## Self-healing broken selectors

### 7. Fix a broken locator after a UI change (static diagnosis)

```
tests/test_checkout.py is failing with:

  playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms
  exceeded.
  Call log:
    - waiting for locator("#old-checkout-btn")

The checkout button's id likely changed in a recent UI update. Look at the
CheckoutPage object in pages/checkout_page.py, and propose an updated
locator using a role/accessible-name-based strategy instead of a raw id
selector, consistent with the locator guidance in Tutorial 4. If you
cannot determine the new markup from the repo alone, say so instead of
guessing.
```

### 8. Self-heal using the Playwright MCP server (live inspection)

*Requires the `playwright` MCP server connected — see README "Installing
the Playwright MCP server."*

```
The locator in pages/checkout_page.py (page.locator("#old-checkout-btn"))
is no longer matching anything on the staging checkout page at
https://staging.example-shop.test/cart. Use the Playwright MCP tools to
navigate there with the test account (credentials from .env, never
production), take an accessibility snapshot of the cart page, and find the
current checkout button's accessible role and name. Then update
CheckoutPage to use page.get_by_role(...) with that name instead of the id
selector, and run the checkout test in
05-playwright-advanced-production-patterns/ to confirm it passes.
```

---

## Exploring an app via MCP

### 9. Discover selectors for an unfamiliar flow

*Requires the `playwright` MCP server connected.*

```
Using the Playwright MCP tools, navigate to https://www.saucedemo.com,
log in as standard_user / secret_sauce, and walk through the "Add to
cart" -> cart -> checkout -> overview -> finish flow. At each step, take
an accessibility snapshot and note the role/name/test-id of the key
interactive elements (add-to-cart buttons, cart badge, checkout button,
continue/finish buttons). Do not write any test code yet — just report
back a list of elements and the best locator strategy for each, so I can
review it before we turn it into a Page Object.
```

### 10. Reproduce a reported bug interactively

*Requires the `playwright` MCP server connected.*

```
QA reported that on staging, adding an item to the cart from the product
detail page (not the inventory list) doesn't update the cart badge. Use
the Playwright MCP tools to navigate to
https://staging.example-shop.test, open a product detail page, click
"Add to cart," and take a snapshot before and after to check the badge
state. Report exactly what you observe (reproduced or not, and what the
DOM/accessibility tree shows) — do not modify any test or page object in
this step, this is reconnaissance only.
```
