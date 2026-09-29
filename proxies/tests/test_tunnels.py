from __future__ import annotations

import asyncio
import sys
import unittest

from model_proxy.config import SshTunnel
from model_proxy.tunnels import Tunnel, ssh_command


class CommandTests(unittest.TestCase):
    def test_ssh_command(self) -> None:
        command = ssh_command(SshTunnel(target="root@203.0.113.10", local_port=18191,
                                        remote_port=18090))
        self.assertEqual(command[0], "ssh")
        self.assertEqual(command[-1], "root@203.0.113.10")
        self.assertEqual(command[command.index("-L") + 1], "127.0.0.1:18191:127.0.0.1:18090")
        for option in ("BatchMode=yes", "ExitOnForwardFailure=yes", "ServerAliveInterval=15"):
            self.assertIn(option, command)
        self.assertIn("-N", command)


class TunnelTests(unittest.IsolatedAsyncioTestCase):
    async def test_exited_tunnel_starts_again_and_keeps_the_message(self) -> None:
        tunnel = Tunnel("t", [sys.executable, "-c",
                              "import sys; sys.stderr.write('refused'); sys.exit(3)"],
                        min_backoff=0.01, max_backoff=0.02)
        tunnel.start()
        try:
            for _ in range(200):
                if tunnel.starts >= 3:
                    break
                await asyncio.sleep(0.02)
            self.assertGreaterEqual(tunnel.starts, 3)
            self.assertEqual(tunnel.last_exit, 3)
            self.assertEqual(tunnel.last_error, "refused")
        finally:
            await tunnel.stop()

    async def test_stop_terminates_a_running_tunnel(self) -> None:
        tunnel = Tunnel("t", [sys.executable, "-c", "import time; time.sleep(60)"])
        tunnel.start()
        for _ in range(200):
            if tunnel.running:
                break
            await asyncio.sleep(0.02)
        self.assertTrue(tunnel.running)
        process = tunnel.process
        await tunnel.stop()
        self.assertFalse(tunnel.running)
        self.assertIsNotNone(process.returncode)
        self.assertEqual(tunnel.status()["starts"], 1)

    async def test_missing_program_is_reported(self) -> None:
        tunnel = Tunnel("t", ["/nonexistent/ssh"], min_backoff=0.01, max_backoff=0.02)
        tunnel.start()
        try:
            for _ in range(100):
                if tunnel.last_error:
                    break
                await asyncio.sleep(0.01)
            self.assertIn("cannot start", tunnel.last_error)
            self.assertFalse(tunnel.running)
        finally:
            await tunnel.stop()


if __name__ == "__main__":
    unittest.main()
