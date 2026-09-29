"""The SSH tunnels to the RTX hosts: one `ssh -N -L` process for each host with an `ssh`
entry.

Read docs/plans/01_multi-host-model-proxy.md, section "Tunnels". The processes stay in the
process group of the proxy, so Ctrl-C in the terminal stops them too.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import subprocess
import time
from collections.abc import Sequence
from typing import Any

from .config import SshTunnel


log = logging.getLogger("model_proxy.tunnels")

SSH_OPTIONS = (
    "-N",
    "-o", "BatchMode=yes",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=3",
    "-o", "ConnectTimeout=10",
)


def ssh_command(tunnel: SshTunnel) -> list[str]:
    """Return the command line of one tunnel."""
    forward = f"127.0.0.1:{tunnel.local_port}:127.0.0.1:{tunnel.remote_port}"
    return ["ssh", *SSH_OPTIONS, "-L", forward, tunnel.target]


class Tunnel:
    """One supervised tunnel process. After an exit, the next start waits `min_backoff`
    seconds, and the wait doubles up to `max_backoff`. A process that ran `stable_after`
    seconds or more starts the wait again at `min_backoff`."""

    def __init__(
        self,
        name: str,
        command: Sequence[str],
        *,
        min_backoff: float = 1.0,
        max_backoff: float = 60.0,
        stable_after: float = 60.0,
    ) -> None:
        self.name = name
        self.command = list(command)
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff
        self.stable_after = stable_after
        self.process: asyncio.subprocess.Process | None = None
        self.starts = 0
        self.started_at: float | None = None
        self.last_exit: int | None = None
        self.last_error = ""
        # Set after the first start attempt, so that the first health probe can wait.
        self.spawned = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._stopping = False

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    def start(self) -> None:
        self._task = asyncio.create_task(self._supervise(), name=f"tunnel-{self.name}")

    async def _supervise(self) -> None:
        loop = asyncio.get_running_loop()
        backoff = self.min_backoff
        while not self._stopping:
            began = loop.time()
            try:
                self.process = await asyncio.create_subprocess_exec(
                    *self.command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except OSError as exc:
                self.process = None
                self.last_error = f"cannot start: {exc}"
                self.spawned.set()
                log.error("tunnel %s: %s", self.name, self.last_error)
            else:
                self.spawned.set()
                self.starts += 1
                self.started_at = time.time()
                log.info("tunnel %s started, pid %d: %s", self.name, self.process.pid,
                         " ".join(self.command))
                assert self.process.stderr is not None
                stderr = await self.process.stderr.read()
                self.last_exit = await self.process.wait()
                self.last_error = stderr.decode("utf-8", "replace").strip()[-300:]
                if not self._stopping:
                    log.warning("tunnel %s exited with status %s: %s", self.name,
                                self.last_exit, self.last_error or "no message")
            if self._stopping:
                break
            if loop.time() - began >= self.stable_after:
                backoff = self.min_backoff
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, self.max_backoff)

    async def stop(self) -> None:
        self._stopping = True
        process = self.process
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def status(self) -> dict[str, Any]:
        return {
            "command": " ".join(self.command),
            "running": self.running,
            "pid": self.process.pid if self.running and self.process is not None else None,
            "starts": self.starts,
            "started_at": self.started_at,
            "last_exit": self.last_exit,
            "last_error": self.last_error,
        }
