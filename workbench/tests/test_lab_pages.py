"""Tests of `pipeline/lab_pages.py`: the theme mark and the optional marks of the shared
step view (plan 55)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "pipeline"))
import lab_pages  # noqa: E402

THEME = "/* THEME_CSS */\n"


class MarksTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.pages = Path(self.directory.name)
        for name, text in (("theme.css", ":root{--a:1}\n"), ("steps.css", ".step{}\n"),
                           ("steps.js", "const Steps = 1;\n")):
            (self.pages / name).write_text(text, encoding="utf-8")
        patcher = mock.patch.object(lab_pages, "PAGES_DIR", str(self.pages))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.directory.cleanup)

    def page(self, text):
        (self.pages / "p.html").write_text(text, encoding="utf-8")
        return lab_pages.page("p.html")

    def test_each_mark_gets_its_file(self):
        out = self.page("<style>\n" + THEME + "/* STEPS_CSS */\n</style><script>\n"
                        "/* STEPS_JS */\n</script>")
        self.assertEqual(out, "<style>\n:root{--a:1}\n.step{}\n</style><script>\n"
                              "const Steps = 1;\n</script>")

    def test_a_page_with_no_step_mark_gets_the_theme_alone(self):
        self.assertEqual(self.page("<style>\n" + THEME + "</style>"),
                         "<style>\n:root{--a:1}\n</style>")

    def test_a_mark_twice_is_refused(self):
        with self.assertRaises(ValueError):
            self.page(THEME + "/* STEPS_JS */\n/* STEPS_JS */\n")
        with self.assertRaises(ValueError):
            self.page("no theme")


class RealPagesTest(unittest.TestCase):
    def test_no_page_keeps_a_mark(self):
        for name in sorted(os.listdir(lab_pages.PAGES_DIR)):
            if not name.endswith(".html"):
                continue
            text = lab_pages.page(name)
            for mark in (THEME,) + tuple(mark for mark, _ in lab_pages.PARTS):
                self.assertNotIn(mark, text, name)


if __name__ == "__main__":
    unittest.main()
