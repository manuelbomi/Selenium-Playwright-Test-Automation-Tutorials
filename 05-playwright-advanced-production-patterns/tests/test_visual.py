"""
Visual regression testing with expect(page).to_have_screenshot().

Unlike a functional assertion (does this element exist / contain this text),
a visual assertion catches things nothing else does: a broken CSS grid, an
overlapping element, a font that failed to load, a color regression -- the
kind of bug that "the DOM is technically correct" tests sail right past.

HOW BASELINES WORK
-------------------
The first time this test runs, there is no baseline image to compare
against, so it FAILS with a "no baseline found" message and writes the
screenshot it captured to disk. Review that image, and if it looks right,
promote it to the baseline by re-running with --update-snapshots:

    pytest tests/test_visual.py --update-snapshots

This creates/updates a PNG under tests/test_visual.py-snapshots/ next to
this file. COMMIT that baseline PNG to git -- it's the "expected" image
every future run is diffed against. Every subsequent run compares the live
page to that baseline and fails if the pixel difference exceeds the
tolerance (see max_diff_pixel_ratio below).

PITFALLS
--------
Visual tests are the flakiest kind of test if run inconsistently:
  - Font rendering differs across OS (Windows/macOS/Linux render the same
    font with different anti-aliasing/hinting), so a baseline captured on a
    developer's Windows laptop WILL mismatch on Linux-based CI runners.
  - Browser/OS minor version bumps can shift sub-pixel rendering.
  - Dynamic content (dates, ads, animations) needs to be masked or disabled,
    or every run will "regress" against last month's baseline.

The fix: generate and check baselines in the SAME environment tests run in --
in practice, this means running visual tests inside the project's Docker
image (see ../Dockerfile) both locally and in CI, never comparing a
locally-captured baseline against a CI-rendered screenshot or vice versa.
"""

from playwright.sync_api import Page, expect


def test_login_page_visual(page: Page):
    page.goto("/")

    # Wait for a stable, meaningful element before snapshotting -- taking the
    # screenshot one frame too early (before fonts/layout settle) is the
    # single most common source of false-positive visual diffs.
    expect(page.get_by_placeholder("Username")).to_be_visible()

    expect(page).to_have_screenshot(
        "login-page.png",
        # Small tolerance for anti-aliasing noise, not for real regressions.
        max_diff_pixel_ratio=0.02,
    )
