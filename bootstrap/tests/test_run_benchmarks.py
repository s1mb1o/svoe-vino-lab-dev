from __future__ import annotations

import argparse
import unittest
from pathlib import Path

from scripts.run_benchmarks import _command


class BenchmarkRunnerCommandTest(unittest.TestCase):
    def arguments(self, device: str) -> argparse.Namespace:
        return argparse.Namespace(
            root=Path("/bootstrap"),
            model_root=Path("/models"),
            python=Path("/venv/bin/python"),
            qr_python=Path("/venv/bin/python"),
            port=18090,
            device=device,
        )

    def test_mps_shieldgemma_uses_float32(self) -> None:
        command = _command(self.arguments("mps"), "shieldgemma-2-4b-it")
        self.assertEqual(command[command.index("--device") + 1], "mps")
        self.assertEqual(command[command.index("--dtype") + 1], "float32")

    def test_cuda_shieldgemma_uses_bfloat16(self) -> None:
        command = _command(self.arguments("cuda"), "shieldgemma-2-4b-it")
        self.assertEqual(command[command.index("--dtype") + 1], "bfloat16")

    def test_mps_sam3_uses_fp16(self) -> None:
        command = _command(self.arguments("mps"), "sam3")
        self.assertEqual(command[command.index("--device") + 1], "mps")
        self.assertEqual(command[command.index("--dtype") + 1], "fp16")


if __name__ == "__main__":
    unittest.main()
