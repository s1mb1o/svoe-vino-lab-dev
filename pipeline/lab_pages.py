"""Read the HTML pages that `pipeline/lab_server.py` and `scripts/review_server.py` share.

A page file is in `pipeline/pages/`. The shared colour theme is in
`pipeline/pages/theme.css`. A page holds the line `/* THEME_CSS */` inside its
`<style>` element, and `page` puts the theme in place of that line.
"""
import os
import re

PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
THEME_MARK = "/* THEME_CSS */\n"
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
    """Return the page `name` with the shared theme in place of its mark."""
    text = _read(name)
    if text.count(THEME_MARK) != 1:
        raise ValueError("%s MUST hold the mark %r exactly one time"
                         % (name, THEME_MARK.strip()))
    return text.replace(THEME_MARK, theme_css())
