# Official Playwright Python image: ships Python, Playwright, and every
# browser + OS-level dependency (fonts, codecs, etc.) already installed and
# version-matched to the Playwright release. Using this instead of a plain
# `python:3.x` base eliminates an entire class of "works on my machine but
# not in CI" failures caused by mismatched or missing system libraries --
# and it's also what makes visual-regression baselines reproducible (see
# tests/test_visual.py): every environment running this image renders fonts
# identically.
#
# Pin the tag to the same Playwright version as requirements.txt so the
# browsers baked into the image match the `playwright` pip package installed
# below. Mismatched versions are a common source of "browser not found" or
# subtly different rendering.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

# Install Python deps first, separately from the app source, so Docker's
# layer cache keeps this step cached across builds that only change test code.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# NOTE: no `playwright install --with-deps` here -- the base image already
# has the browsers and OS deps baked in. Running install again would just
# waste build time re-downloading what's already present.

COPY . .

# Default command: run the full suite in parallel, keep traces only for
# failing tests (cheap on disk, invaluable for debugging), and produce a
# self-contained HTML report. Override at `docker run` time for ad hoc runs,
# e.g. `docker run <image> pytest tests/test_visual.py --update-snapshots`.
CMD ["pytest", "-n", "auto", "--tracing=retain-on-failure", "--html=report.html", "--self-contained-html"]
