"""A catalogue merge preserves vintage links in its transaction."""
import unittest
import wine_vintages
import wine_merge
import test_wine_merge as WM
SOURCE, TARGET = WM.SOURCE, WM.TARGET


class VintageMergeTest(unittest.TestCase):
    setUp = WM.WineMergeTest.setUp
    tearDown = WM.WineMergeTest.tearDown

    def test_merge_transfers_the_vintage_links(self):
        with self.conn:
            wine_vintages.add(self.conn, SOURCE, TARGET)
            wine_vintages.add(self.conn, SOURCE, "neighbor")
            wine_vintages.add(self.conn, TARGET, "neighbor")
        wine_merge.merge(self.db, {"slug": SOURCE, "to": TARGET})
        self.assertEqual(wine_vintages.pairs(self.conn), [("neighbor", TARGET)])
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])


if __name__ == '__main__':
    unittest.main()
