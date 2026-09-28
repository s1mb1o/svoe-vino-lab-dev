from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from launcher import MODELS, _command, _watch_processes


class LauncherCommandTest(unittest.TestCase):
    def shield_command(self, device: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            model_root = Path(directory)
            (model_root / "google--shieldgemma-2-4b-it").mkdir()
            return _command(MODELS["shieldgemma-2-4b-it"], 18091, model_root, device)

    def test_shieldgemma_uses_float32_on_mps(self) -> None:
        command = self.shield_command("mps")
        self.assertEqual(command[command.index("--dtype") + 1], "float32")

    def test_shieldgemma_uses_bfloat16_on_cuda(self) -> None:
        command = self.shield_command("cuda")
        self.assertEqual(command[command.index("--dtype") + 1], "bfloat16")

    def test_process_exit_stops_gateway(self) -> None:
        server = MagicMock()
        server.should_exit = False
        process = MagicMock()
        process.poll.return_value = 17
        failure: list[tuple[str, int]] = []
        _watch_processes(server, {"sam3": process}, threading.Event(), failure)
        self.assertTrue(server.should_exit)
        self.assertEqual(failure, [("sam3", 17)])


if __name__ == "__main__":
    unittest.main()
