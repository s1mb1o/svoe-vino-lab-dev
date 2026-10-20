"""Apply a recorded score floor to one new Testset Run without changing its backend."""

import math


DEFAULT_MIN_SCORE = 0.7


def checked(value, default=DEFAULT_MIN_SCORE):
    value = default if value is None else value
    if (type(value) not in (int, float) or not 0 <= value <= 1
            or not math.isfinite(value)):
        raise ValueError("min_score MUST be a finite number from 0 to 1")
    return float(value)


class ScoreThreshold:
    """Keep raw rejected candidates in the trace. A missing score is not a zero."""

    def __init__(self, backend, min_score):
        self.inner = backend
        self.min_score = checked(min_score)
        self.spec = dict(backend.spec, min_score=self.min_score)

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def ask(self, path):
        answer = list(self.inner.ask(path))
        candidates = answer[0]
        if self.min_score == 0 or not candidates or answer[3]:
            return tuple(answer)
        score = candidates[0].get("score")
        numeric = type(score) in (int, float)
        accepted = not numeric or (math.isfinite(score) and score >= self.min_score)
        audit = {"min_score": self.min_score, "score": score,
                 "applied": numeric, "accepted": accepted}
        if not accepted:
            audit["raw_candidates"] = candidates
            answer[0] = []
        if len(answer) < 5:
            answer.append({})
        answer[4] = dict(answer[4] or {}, score_threshold=audit)
        return tuple(answer)
