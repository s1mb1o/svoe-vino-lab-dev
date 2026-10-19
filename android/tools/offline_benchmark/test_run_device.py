"""Reject a cached or unprotected device before inference."""
import unittest

from run_device import require_foreground


class ForegroundGuardTest(unittest.TestCase):
    def test_visible_and_foreground_service(self):
        for importance in (100,125):
            require_foreground(dict(foreground_service=True,wake_lock_held=True,process_importance=importance))

    def test_rejects_missing_service_or_wake_lock(self):
        for field in ('foreground_service','wake_lock_held'):
            health=dict(foreground_service=True,wake_lock_held=True,process_importance=125)
            health[field]=False
            with self.assertRaises(RuntimeError):require_foreground(health)

    def test_rejects_cached_or_old_server(self):
        for health in ({},dict(foreground_service=True,wake_lock_held=True,process_importance=400)):
            with self.assertRaises(RuntimeError):require_foreground(health)


if __name__=='__main__':unittest.main()
