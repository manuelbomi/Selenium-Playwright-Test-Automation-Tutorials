"""
Network interception & mocking with page.route().

This is a capability Selenium has no built-in equivalent for. Playwright sits
in the middle of every network request the browser makes and lets you
inspect, modify, mock, or block it -- with zero cooperation required from the
real backend. In production suites this is used to:
  - reproduce backend error states (500s, timeouts, malformed JSON) on demand,
    to test error UI without waiting for a real outage or standing up a fake
    backend
  - strip out flaky third-party dependencies (analytics, ads, payment widgets)
    that have nothing to do with what the test is verifying
  - inspect the on-the-wire requests themselves for debugging/assertions

saucedemo.com is a static demo app with no JSON API to mock (its "inventory"
is hardcoded client-side JS, not fetched from a server), so we demonstrate the
technique against the most realistic interceptable network call it actually
makes: the product image requests. The pattern below --
match a URL, then `route.fulfill(status=500, ...)` -- is EXACTLY what you'd
use against a real `fetch("/api/products")` call to simulate the API being
down; only the URL pattern and response body would change.
"""

import re

from playwright.sync_api import Page, expect


def test_observe_all_network_requests(authenticated_page: Page):
    """
    Plain interception/observation, with no mocking: every request the page
    makes can be logged and asserted on. This answers questions Selenium
    cannot answer without an external proxy -- "did this analytics beacon
    actually fire?", "why is this page slow?", "is this 3rd-party script even
    loading?" -- directly inside the test.
    """
    seen_urls: list[str] = []

    def record_request(route):
        seen_urls.append(route.request.url)
        route.continue_()  # let the real request through unmodified

    authenticated_page.route("**/*", record_request)
    authenticated_page.goto("/inventory.html")
    authenticated_page.wait_for_load_state("networkidle")

    assert len(seen_urls) > 0
    assert any("saucedemo.com" in url for url in seen_urls)


def test_simulated_backend_failure_on_product_images(authenticated_page: Page):
    """
    Simulates a backend/CDN outage for product images by fulfilling every
    image request with a 500 -- without touching the real server at all.

    On an app backed by a real API, this exact call --
        route.fulfill(status=500, content_type="application/json",
                       body='{"error": "internal server error"}')
    -- is how you'd force a product list, checkout, or search endpoint into
    an error state, to verify the UI shows a friendly error message instead
    of a blank screen or an unhandled exception. That's the technique this
    test is demonstrating.

    saucedemo doesn't ship a custom "image failed to load" UI, so the
    observable effect here is the browser's native broken-image state
    (naturalWidth/naturalHeight collapse to 0 when a mocked failure response
    is served instead of real image bytes). The assertion strategy --
    "critical content still renders even though a dependent resource
    failed" -- is exactly what you'd reuse against a real error-state test.
    """
    image_pattern = re.compile(r"\.(jpg|jpeg|png|webp)(\?.*)?$", re.IGNORECASE)

    def fail_image_request(route):
        route.fulfill(
            status=500,
            content_type="text/plain",
            body="Simulated backend failure: image service unavailable",
        )

    authenticated_page.route(image_pattern, fail_image_request)
    authenticated_page.goto("/inventory.html")

    # Product name/price rendering doesn't depend on the image CDN -- this is
    # exactly the kind of resilience a mocked failure lets you verify on
    # demand, instead of waiting for a real outage to find out.
    expect(authenticated_page.get_by_text("Sauce Labs Backpack")).to_be_visible()

    first_image = authenticated_page.locator("img.inventory_item_img").first
    # naturalWidth is 0 on a broken <img> -- proof the mocked 500 was served
    # in place of real image bytes, and the browser gave up rendering it.
    natural_width = first_image.evaluate("img => img.naturalWidth")
    assert natural_width == 0
