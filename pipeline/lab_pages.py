"""Read the HTML pages that `pipeline/lab_server.py` and `scripts/review_server.py` share.

A page file is in `pipeline/pages/`. The shared colour theme is in
`pipeline/pages/theme.css`. A page holds the line `/* THEME_CSS */` inside its
`<style>` element, and `page` puts the theme in place of that line.

The step view of one photo (plan 41) is in `pipeline/pages/steps.css` and
`pipeline/pages/steps.js`; `/runs` and `/recognize` share it (plan 55). A page MAY hold
the line `/* STEPS_CSS */` inside its `<style>` element and the line `/* STEPS_JS */`
inside its `<script>` element, each one time at most. `page` puts the file in place of
the line. A page with no such line does not change.
"""
import os
import re

PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
THEME_MARK = "/* THEME_CSS */\n"
# The optional marks and their files (plan 55).
PARTS = (("/* STEPS_CSS */\n", "steps.css"), ("/* STEPS_JS */\n", "steps.js"))
# The Dataset page with the image preview of one wine open: `/dataset/<slug>` shows the
# catalogue image, `/dataset/<slug>/patch` the patch image, and
# `/dataset/<slug>/alternative/<sha256>` one alternative photo. The page reads the path.
DATASET_PREVIEW_ROUTE = re.compile(r"^/dataset/[^/]+(/patch|/alternative/[0-9a-f]{64})?$")


def _read(name):
    with open(os.path.join(PAGES_DIR, name), encoding="utf-8", newline="") as fh:
        return fh.read()


def theme_css():
    """Return the shared colour theme: light and dark, after the system setting."""
    return _read("theme.css")


def page(name):
    """Return the page `name` with the shared theme in place of its mark, and each shared
    part in place of its optional mark."""
    text = _read(name)
    if text.count(THEME_MARK) != 1:
        raise ValueError("%s MUST hold the mark %r exactly one time"
                         % (name, THEME_MARK.strip()))
    for mark, part in PARTS:
        if text.count(mark) > 1:
            raise ValueError("%s MAY hold the mark %r one time at most" % (name, mark.strip()))
    text = text.replace(THEME_MARK, theme_css())
    for mark, part in PARTS:
        if mark in text:
            text = text.replace(mark, _read(part))
    return text
