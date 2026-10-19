from __future__ import annotations

from chto_za_vino_account.limits import SlidingWindow


def test_prune_runs_at_most_once_a_window(monkeypatch):
    now = [0.0]
    window = SlidingWindow(1, 60, lambda: now[0])
    calls = []
    original = window._prune
    monkeypatch.setattr(window, "_prune", lambda at: (calls.append(at), original(at)))
    for number in range(50_100):
        window.record(f"key-{number}")
    assert len(calls) == 1
    now[0] = 61.0
    window.record("late")
    assert len(calls) == 2
    # Only the keys of the current window remain.
    assert set(window._events) == {"late"}
