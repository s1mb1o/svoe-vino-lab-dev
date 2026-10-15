"""Check vintage links in every cluster view and the artifact identity."""
import tempfile
import unittest
from test_clusters import ClusterLab
import clusters
import embeddings
import wine_vintages
class VintageClusterTest(unittest.TestCase):
    """The vintage pairs of `wine_vintage` in the build (plan 62)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = ClusterLab(self.tmp.name)

    def tearDown(self):
        self.fixture.close()
        self.tmp.cleanup()

    def pair(self, slug, other):
        with self.fixture.lab.conn:
            wine_vintages.add(self.fixture.lab.conn, slug, other, "2026-09-27T12:00:00Z")

    def build(self):
        context = clusters.context(self.fixture.settings, "gw")
        vectors = embeddings.read_vectors(self.fixture.lab.entry_dir(), context["index"])
        return clusters.build(context, vectors, 0.95, 0.95)

    @staticmethod
    def members(artifact, space):
        return {tuple(cluster["slugs"]): cluster for cluster in
                artifact["spaces"][space]["clusters"]}

    def test_a_pair_merges_two_clusters_in_each_view(self):
        # The label view has {grey, patched} and {shared, transparent}.
        self.pair("shared", "patched")
        artifact = self.build()
        label = self.members(artifact, "label")
        self.assertEqual(list(label), [("grey", "patched", "shared", "transparent")])
        cluster = label[("grey", "patched", "shared", "transparent")]
        self.assertEqual((cluster["kind"], cluster["signals"]), ("label", ["label", "vintage"]))
        link = next(edge for edge in cluster["links"]
                    if (edge["a"], edge["b"]) == ("patched", "shared"))
        self.assertEqual((link["by"], link["spaces"]), (["vintage"], {}))
        # The full view had {grey, shared, transparent}; patched joins it.
        self.assertEqual(list(self.members(artifact, "full")),
                         [("grey", "patched", "shared", "transparent")])
        combined = self.members(artifact, "combined")[("grey", "patched", "shared",
                                                       "transparent")]
        self.assertEqual((combined["kind"], combined["signals"]),
                         ("mixed", ["full", "label", "vintage"]))

    def test_a_pair_with_a_vector_link_gets_vintage_in_by(self):
        self.pair("grey", "patched")
        cluster = self.members(self.build(), "label")[("grey", "patched")]
        link = next(edge for edge in cluster["links"]
                    if (edge["a"], edge["b"]) == ("grey", "patched"))
        self.assertEqual(link["by"], ["label", "vintage"])
        self.assertIn("label", link["spaces"])

    def test_a_pair_of_two_wines_with_no_link_is_a_vintage_cluster(self):
        self.pair("unprocessed", "patched")
        full = self.members(self.build(), "full")
        cluster = full[("patched", "unprocessed")]
        self.assertEqual((cluster["kind"], cluster["signals"], cluster["size"]),
                         ("vintage", ["vintage"], 2))

    def test_a_pair_with_a_wine_out_of_the_build_changes_nothing(self):
        before = clusters.context(self.fixture.settings, "gw")["input_hash"]
        self.pair("disabled", "unprocessed")
        context = clusters.context(self.fixture.settings, "gw")
        self.assertEqual(context["vintage"], [])
        self.assertEqual(context["input_hash"], before)
        self.assertNotIn(("disabled", "unprocessed"), self.members(self.build(), "full"))

    def test_a_new_pair_makes_the_artifact_stale(self):
        clusters.build_to_directory(self.fixture.settings, "gw")
        self.assertFalse(clusters.artifact_status(self.fixture.settings, "gw")["stale"])
        self.pair("unprocessed", "patched")
        self.assertTrue(clusters.artifact_status(self.fixture.settings, "gw")["stale"])



    def test_an_undated_hub_connects_multiple_vintages(self):
        self.pair("grey", "patched")
        self.pair("grey", "unprocessed")
        artifact = self.build()
        for space in ["full", "label", "combined"]:
            group = next(group for group in artifact["spaces"][space]["clusters"]
                         if "grey" in group["slugs"])
            self.assertTrue({"grey", "patched", "unprocessed"}.issubset(group["slugs"]))
            self.assertIn("vintage", group["signals"])

    def test_visual_similarity_and_vintage_keep_separate_reasons(self):
        import similar_wines
        self.pair("grey", "patched")
        with self.fixture.lab.conn:
            similar_wines.add(self.fixture.lab.conn, "grey", "patched")
        group = self.members(self.build(), "label")[("grey", "patched")]
        edge = next(edge for edge in group["links"]
                    if (edge["a"], edge["b"]) == ("grey", "patched"))
        self.assertEqual(edge["by"], ["label", "manual", "vintage"])
        self.assertEqual(group["signals"], ["label", "manual", "vintage"])


    def test_an_inactive_hub_keeps_its_active_vintages_in_one_cluster(self):
        self.pair("disabled", "patched")
        self.pair("disabled", "unprocessed")
        context = clusters.context(self.fixture.settings, "gw")
        self.assertEqual(context["vintage"], [["patched", "unprocessed"]])
        group = self.members(self.build(), "full")[("patched", "unprocessed")]
        self.assertEqual(group["signals"], ["vintage"])
        self.assertNotIn("disabled", group["slugs"])


if __name__ == '__main__':
    unittest.main()
