"""Read the HTML pages that `pipeline/lab_server.py` and `scripts/review_server.py` share.

A page file is in `pipeline/pages/`. The shared colour theme is in
`pipeline/pages/theme.css`. A page holds the line `/* THEME_CSS */` inside its
`<style>` element, and `page` puts the theme in place of that line.

The step view of one photo (plan 41) is in `pipeline/pages/steps.css` and
`pipeline/pages/steps.js`; `/runs` and `/recognize` share it (plan 55). A page MAY hold
the line `/* STEPS_CSS */` inside its `<style>` element and the line `/* STEPS_JS */`
inside its `<script>` element, each one time at most. `page` puts the file in place of
the line. A page with no such line does not change.

The drop of a local image from the Codex desktop app is in `pipeline/pages/drop.js`;
`/testset`, `/dataset`, and `/recognize` share it. A page MAY hold the line
`/* DROP_JS */` inside its `<script>` element one time at most, by the same rule.
"""
import os
import re

PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
THEME_MARK = "/* THEME_CSS */\n"
# The optional marks and their files (plan 55).
PARTS = (("/* STEPS_CSS */\n", "steps.css"), ("/* STEPS_JS */\n", "steps.js"),
         ("/* DROP_JS */\n", "drop.js"), ("/* VISIBLE_CARDS_JS */\n", "visible_cards.js"),
         ("/* CONFIGURATION_PICKER_CSS */\n", "configuration_picker.css"),
         ("/* CONFIGURATION_PICKER_JS */\n", "configuration_picker.js"))
# These views retain complete offscreen rows. Share browser layout deferral without
# changing the row DOM or the existing table and mobile layouts.
DEFER_LAYOUT_PAGES = frozenset(("testset.html", "clusters.html"))
CARD_PREVIEW_PAGES = frozenset(("dataset.html", "testset.html", "runs.html"))
# The Dataset page with the image preview of one wine open: `/dataset/<slug>` shows the
# catalogue image, `/dataset/<slug>/patch` the patch image, and
# `/dataset/<slug>/alternative/<sha256>` one alternative photo. The page reads the path.
# `/dataset/<slug>/describe/<sha256>` opens the image description dialog of one image.
DATASET_PREVIEW_ROUTE = re.compile(
    r"^/dataset/[^/]+(/patch|/(?:alternative|describe)/[0-9a-f]{64})?$")


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
    if name in DEFER_LAYOUT_PAGES:
        if "</style>" not in text:
            raise ValueError("%s MUST hold a style element" % name)
        text = text.replace("</style>", _read("page_rendering.css") + "</style>", 1)
    if name in CARD_PREVIEW_PAGES:
        if "</head>" not in text:
            raise ValueError("%s MUST hold a head element" % name)
        text = text.replace("</head>", "<script>" + _read("first_images.js")
                            + "</script></head>", 1)
    return text
