from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from scripts.smoke import embedding, sam3


def response(payload: dict[str, object]) -> MagicMock:
    result = MagicMock()
    result.json.return_value = payload
    return result


class SmokeTest(unittest.TestCase):
    def test_naflex_checks_all_required_patch_budgets(self) -> None:
        client = MagicMock()
        vector = [1.0] + [0.0] * 1151
        client.post.return_value = response({"data": [{"embedding": vector}]})

        result = embedding(
            client,
            "http://127.0.0.1:18090",
            "siglip2-so400m-patch16-naflex",
        )

        budgets = [call.kwargs["json"]["max_num_patches"] for call in client.post.call_args_list]
        self.assertEqual(budgets, [256, 512, 1024])
        self.assertEqual(set(result["budgets"]), {"256", "512", "1024"})

    def test_sam3_rejects_an_empty_detection(self) -> None:
        client = MagicMock()
        client.post.return_value = response(
            {"count": 0, "width": 320, "height": 480, "instances": []}
        )
        with self.assertRaisesRegex(AssertionError, "did not find"):
            sam3(client, "http://127.0.0.1:18090")

    def test_sam3_accepts_a_nonempty_detection(self) -> None:
        client = MagicMock()
        client.post.return_value = response(
            {
                "count": 1,
                "width": 320,
                "height": 480,
                "instances": [{"label": "wine bottle"}],
            }
        )
        self.assertEqual(sam3(client, "http://127.0.0.1:18090")["count"], 1)


if __name__ == "__main__":
    unittest.main()
