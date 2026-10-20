"""Request deadlines include decoding and completed service timeouts."""

import asyncio
from time import perf_counter
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from matcher.cascade import Cascade, CascadeConfig, Sam3Config
from matcher.cascade_run import Budget, Run
from matcher.group import GroupMatchError
from matcher.photo import Sam3Copy


class Services:
    async def close(self):
        pass


class DecodeDeadlineTest(unittest.IsolatedAsyncioTestCase):
    def cascade(self, config=CascadeConfig()):
        bundle = SimpleNamespace(embedding={"model": "test"}, cards={})
        cascade = Cascade(config, bundle, Services(), cpu_workers=1)
        self.addAsyncCleanup(cascade.close)
        return cascade

    async def test_expired_request_does_not_decode_or_start_services(self):
        cascade = self.cascade()
        now = perf_counter()
        with patch("matcher.cascade_run.photo.decode", side_effect=AssertionError("decode")):
            slug, trace = await cascade.predict(b"unread", Budget(now, hard_at=now - 1))
        self.assertEqual(slug, "")
        self.assertEqual(trace["decision"]["reason"], "timeout")
        self.assertEqual(trace["stages"], [])

    async def test_running_decode_returns_at_hard_limit_without_waiting_for_thread(self):
        cascade = self.cascade()
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        def decode(body):
            entered.set()
            release.wait(5)
            finished.set()
            return Image.new("RGB", (1, 1))
        try:
            with patch("matcher.cascade_run.photo.decode", decode):
                now = perf_counter()
                task = asyncio.create_task(cascade.predict(b"unread", Budget(now, hard_at=now + .3)))
                while not entered.is_set() and not task.done():
                    await asyncio.sleep(.005)
                slug, trace = await task
            self.assertTrue(entered.is_set())
            self.assertFalse(finished.is_set())
            self.assertEqual(slug, "")
            self.assertEqual(trace["decision"]["reason"], "timeout")
            self.assertEqual(trace["stages"], [])
            self.assertLess(perf_counter() - now, 1)
        finally:
            release.set()

    async def test_service_timeout_at_hard_limit_returns_empty_timeout(self):
        cascade = self.cascade(CascadeConfig(whole_image=False, sam3=Sam3Config(),
                                             label_only=True))
        clock = [10.0]
        async def segment(*args, **kwargs):
            clock[0] = 11.0
            raise GroupMatchError(504, "SAM3 request timed out")
        cascade.services.segment = segment
        image = Image.new("RGB", (1, 1))
        copy = Sam3Copy(image, b"copy", "image/jpeg", 1, 1)
        with patch("matcher.cascade_run.perf_counter", lambda: clock[0]), \
                patch("matcher.cascade_run.photo.decode", return_value=image), \
                patch("matcher.cascade_run.photo.sam3_copy", return_value=copy):
            slug, trace = await cascade.predict(b"unread", Budget(10, hard_at=11))
        self.assertEqual(slug, "")
        self.assertEqual(trace["decision"]["reason"], "timeout")
        self.assertEqual(trace["stages"][0]["status"], "error")

    async def test_deadline_that_passes_during_task_selection_does_not_wait_forever(self):
        cascade = self.cascade(CascadeConfig(whole_image=False, sam3=Sam3Config(),
                                             label_only=True))
        async def segment(*args, **kwargs):
            await asyncio.Event().wait()
        cascade.services.segment = segment
        clock = [10.0]
        def useful(run, name, answer):
            clock[0] = 11.0
            return True
        with patch("matcher.cascade_run.perf_counter", lambda: clock[0]), \
                patch("matcher.cascade_run.photo.decode", return_value=Image.new("RGB", (1, 1))), \
                patch.object(Run, "useful", useful):
            slug, trace = await asyncio.wait_for(
                cascade.predict(b"unread", Budget(10, hard_at=11)), timeout=1)
        self.assertEqual(slug, "")
        self.assertEqual(trace["decision"]["reason"], "timeout")


if __name__ == "__main__":
    unittest.main()
