"""Comparable competitor pipeline actions for plan 91.

The module adapts public architecture ideas to one catalogue and one benchmark harness.
It does not reproduce competitor-trained weights. Each action wraps the normal embedding
backend and keeps its evidence in the candidate records and the run trace.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from contextlib import closing
from pathlib import Path

try:
    from rapidfuzz.distance import Levenshtein as RapidLevenshtein
except ImportError:  # The lab server does not need the optional fast benchmark runtime.
    RapidLevenshtein = None

import embeddings
import wine_terms
from embeddings import ConfigError


ACTIONS = {
    "view_fusion", "ocr_rerank", "ocr_union", "secondary_union", "sift_rerank",
    "reject",
}
PROFILES = {"stan", "structured"}
SCORE_FIELDS = {"score", "visual_score", "fusion_score", "primary_score"}
TOP_KEYS = {"source", "pool", "secondary", "actions"}
ACTION_KEYS = {
    "view_fusion": {"action", "weights"},
    "ocr_rerank": {"action", "profile", "top_k", "alpha", "conflict_penalty"},
    "ocr_union": {"action", "top_k", "alpha"},
    "secondary_union": {"action", "primary_weight", "secondary_weight"},
    "sift_rerank": {"action", "top_k", "weight"},
    "reject": {"action", "min_score", "min_margin", "score_field"},
}
SECONDARY_KEYS = {"embedding", "views", "top_k"}
YEAR = re.compile(r"^(?:19|20)\d{2}$")
TOKEN = re.compile(r"[a-z0-9]+")

CYRILLIC = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})

GROUPS = {
    "colour": {
        "red": ("red", "krasnoe", "krasnyi"),
        "white": ("white", "beloe", "belyi"),
        "rose": ("rose", "roze", "rozovoe", "rozovyi"),
        "orange": ("orange", "oranzhevoe", "oranzhevyi"),
    },
}


def _number(value, label, low=0.0, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"competitor.{label} MUST be a number")
    value = float(value)
    if value < low or (high is not None and value > high):
        end = f" and {high}" if high is not None else " or more"
        raise ConfigError(f"competitor.{label} MUST be between {low}{end}")
    return value


def _integer(value, label, low=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise ConfigError(f"competitor.{label} MUST be an integer of at least {low}")
    return value


def check_options(raw):
    """Validate and normalize the `competitor` mapping of one embedding pipeline."""
    if not isinstance(raw, dict):
        raise ConfigError("competitor MUST be a mapping")
    unknown = sorted(set(raw) - TOP_KEYS)
    if unknown:
        raise ConfigError("competitor has the unknown key %s" % ", ".join(unknown))
    source = raw.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ConfigError("competitor.source MUST be a non-empty string")
    pool = _integer(raw.get("pool", 30), "pool")
    actions = raw.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ConfigError("competitor.actions MUST be a non-empty list")
    secondary = raw.get("secondary")
    if secondary is not None:
        if not isinstance(secondary, dict):
            raise ConfigError("competitor.secondary MUST be a mapping")
        other = sorted(set(secondary) - SECONDARY_KEYS)
        if other:
            raise ConfigError("competitor.secondary has the unknown key %s" % ", ".join(other))
        name = secondary.get("embedding")
        if not isinstance(name, str) or not embeddings.NAME_RE.match(name):
            raise ConfigError("competitor.secondary.embedding MUST name an embedding")
        secondary = dict(secondary)
        secondary["top_k"] = _integer(secondary.get("top_k", 30), "secondary.top_k")

    checked = []
    for position, raw_action in enumerate(actions):
        if not isinstance(raw_action, dict):
            raise ConfigError(f"competitor.actions[{position}] MUST be a mapping")
        name = raw_action.get("action")
        if name not in ACTIONS:
            raise ConfigError("competitor: unknown action %r; use %s"
                              % (name, ", ".join(sorted(ACTIONS))))
        other = sorted(set(raw_action) - ACTION_KEYS[name])
        if other:
            raise ConfigError("competitor action %s has the unknown key %s"
                              % (name, ", ".join(other)))
        action = dict(raw_action)
        if name == "view_fusion":
            weights = action.get("weights")
            if (not isinstance(weights, dict) or not weights
                    or not all(isinstance(key, str) and key in embeddings.VIEWS
                               for key in weights)):
                raise ConfigError("competitor.view_fusion.weights MUST map known views")
            action["weights"] = {
                key: _number(value, f"view_fusion.weights.{key}", 0.0)
                for key, value in weights.items()
            }
            if not sum(action["weights"].values()):
                raise ConfigError("competitor.view_fusion.weights MUST have a positive sum")
        elif name == "ocr_rerank":
            profile = action.get("profile", "structured")
            if profile not in PROFILES:
                raise ConfigError("competitor.ocr_rerank.profile MUST be stan or structured")
            action.update({
                "profile": profile,
                "top_k": _integer(action.get("top_k", 10), "ocr_rerank.top_k"),
                "alpha": _number(action.get("alpha", 0.18), "ocr_rerank.alpha", 0.0, 1.0),
                "conflict_penalty": _number(action.get("conflict_penalty", 0.08),
                                             "ocr_rerank.conflict_penalty", 0.0, 1.0),
            })
        elif name == "ocr_union":
            action.update({
                "top_k": _integer(action.get("top_k", 10), "ocr_union.top_k"),
                "alpha": _number(action.get("alpha", 0.18), "ocr_union.alpha", 0.0, 1.0),
            })
        elif name == "secondary_union":
            if secondary is None:
                raise ConfigError("competitor.secondary_union requires competitor.secondary")
            action.update({
                "primary_weight": _number(action.get("primary_weight", 0.7),
                                          "secondary_union.primary_weight", 0.0, 1.0),
                "secondary_weight": _number(action.get("secondary_weight", 0.3),
                                            "secondary_union.secondary_weight", 0.0, 1.0),
            })
            if action["primary_weight"] + action["secondary_weight"] <= 0:
                raise ConfigError("competitor.secondary_union weights MUST have a positive sum")
        elif name == "sift_rerank":
            action.update({
                "top_k": _integer(action.get("top_k", 5), "sift_rerank.top_k"),
                "weight": _number(action.get("weight", 0.05), "sift_rerank.weight", 0.0, 1.0),
            })
        elif name == "reject":
            field = action.get("score_field", "score")
            if field not in SCORE_FIELDS:
                raise ConfigError("competitor.reject.score_field MUST be one of %s"
                                  % ", ".join(sorted(SCORE_FIELDS)))
            action.update({
                "min_score": _number(action.get("min_score"), "reject.min_score", -1.0, 1.0),
                "min_margin": _number(action.get("min_margin", 0.0),
                                      "reject.min_margin", 0.0, 2.0),
                "score_field": field,
            })
        checked.append(action)
    return {"source": source, "pool": pool, "secondary": secondary, "actions": checked}


def load_catalog(db_path):
    """Read the text fields of every Active wine for OCR scoring."""
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT wine_slug, COALESCE(name_patched, name), producer, category, color, "
            "COALESCE(grapes, '') FROM wine_catalog WHERE state = 'Active'"
        ).fetchall()
    return {slug: {"slug": slug, "name": name, "producer": producer,
                   "category": category, "color": color, "grapes": grapes}
            for slug, name, producer, category, color, grapes in rows}


def normalize_text(value):
    value = wine_terms.normalize(value).translate(CYRILLIC)
    return " ".join(TOKEN.findall(value))


def tokens(value):
    return [token for token in normalize_text(value).split()
            if len(token) >= 2 or YEAR.match(token)]


def fuzzy(a, b):
    if RapidLevenshtein is not None:
        return float(RapidLevenshtein.normalized_similarity(a, b))
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for index, left in enumerate(a, 1):
        current = [index]
        for position, right in enumerate(b, 1):
            current.append(min(previous[position] + 1, current[-1] + 1,
                               previous[position - 1] + (left != right)))
        previous = current
    return 1.0 - previous[-1] / max(len(a), len(b))


def _coverage(wanted, observed, threshold=0.72):
    if not wanted or not observed:
        return 0.0
    weights = [min(12, max(2, len(token))) for token in wanted]
    values = [max((fuzzy(token, other) for other in observed), default=0.0)
              for token in wanted]
    return sum(weight * value for weight, value in zip(weights, values) if value >= threshold) / sum(weights)


def _candidate_tokens(record):
    return list(dict.fromkeys(tokens(" ".join(str(record.get(key) or "")
                                               for key in ("name", "producer", "grapes")))))


def _attribute_tokens(record):
    return tokens(" ".join(str(record.get(key) or "")
                            for key in ("name", "category", "color", "slug")))


def _group_values(values):
    text = " ".join(values)
    found = {}
    for group, choices in GROUPS.items():
        for value, spellings in choices.items():
            if any(normalize_text(spelling) in text for spelling in spellings):
                found.setdefault(group, set()).add(value)
    sugar_text = wine_terms.base_text(wine_terms.normalize(text))
    sugar = set()
    for kind, pattern in wine_terms.SUGAR:
        bounded = r"\b(?:" + pattern + r")\b"
        if re.search(bounded, sugar_text):
            sugar.add(kind)
            sugar_text = re.sub(bounded, " ", sugar_text)
    if sugar:
        found["sugar"] = sugar
    years = {value for value in values if YEAR.match(value)}
    if years:
        found["year"] = years
    return found


def conflict_count(observed, candidate):
    left, right = _group_values(observed), _group_values(candidate)
    return sum(1 for group, values in left.items()
               if group in right and not values.intersection(right[group]))


def _stan_scores(text, rows, catalog):
    observed = tokens(text)
    names = [_candidate_tokens(catalog.get(row["slug"], {"slug": row["slug"]}))
             for row in rows]
    frequency = {}
    for values in names:
        for value in set(values):
            frequency[value] = frequency.get(value, 0) + 1
    count = len(rows)
    idf = {value: math.log((count + 1) / (seen + 0.5))
           for value, seen in frequency.items()}
    informative = {value for value in observed
                   if any(fuzzy(value, candidate) >= 0.78 for candidate in idf)}
    scores = []
    for row, values in zip(rows, names):
        total = sum(idf[value] for value in values)
        matched = sum(idf[value] * max((fuzzy(value, seen) for seen in observed), default=0.0)
                      for value in values
                      if max((fuzzy(value, seen) for seen in observed), default=0.0) >= 0.78)
        recall = matched / total if total else 0.0
        explained = sum(1 for seen in informative
                        if any(fuzzy(seen, value) >= 0.78 for value in values))
        precision = explained / len(informative) if informative else 0.0
        score = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
        record = catalog.get(row["slug"], {"slug": row["slug"]})
        scores.append((score, conflict_count(observed, _attribute_tokens(record))))
    return scores


def structured_score(text, record):
    observed = tokens(text)
    fields = {
        "name": _coverage(tokens(record.get("name")), observed),
        "producer": _coverage(tokens(record.get("producer")), observed),
        "grapes": _coverage(tokens(record.get("grapes")), observed),
        "category": _coverage(tokens("%s %s" % (record.get("category", ""),
                                                  record.get("color", ""))), observed),
        "vintage": _coverage([value for value in _attribute_tokens(record) if YEAR.match(value)],
                             observed, threshold=0.99),
    }
    score = (0.40 * fields["name"] + 0.30 * fields["producer"]
             + 0.15 * fields["grapes"] + 0.10 * fields["category"]
             + 0.05 * fields["vintage"])
    return score, conflict_count(observed, _attribute_tokens(record)), fields


def _rank(rows):
    out = sorted(rows, key=lambda row: (-float(row.get("score") or -2.0), row["slug"]))
    for rank, row in enumerate(out, 1):
        row["rank"] = rank
    return out


def view_fusion(candidates, weights):
    out = []
    for source in candidates:
        row = dict(source)
        row.setdefault("visual_score", row.get("score"))
        present = [(float(weight), row.get(view)) for view, weight in weights.items()
                   if isinstance(row.get(view), (int, float))]
        if present and sum(weight for weight, _ in present) > 0:
            score = sum(weight * float(value) for weight, value in present) / sum(
                weight for weight, _ in present)
            row["fusion_score"] = row["score"] = round(score, 4)
        out.append(row)
    return _rank(out)


def ocr_rerank(candidates, text, catalog, profile="structured", top_k=10,
               alpha=0.18, conflict_penalty=0.08):
    head, tail = [dict(row) for row in candidates[:top_k]], [dict(row) for row in candidates[top_k:]]
    stan = _stan_scores(text, head, catalog) if profile == "stan" else None
    for position, row in enumerate(head):
        row.setdefault("visual_score", row.get("score"))
        record = catalog.get(row["slug"], {"slug": row["slug"]})
        if stan is not None:
            score, conflicts = stan[position]
            fields = {}
        else:
            score, conflicts, fields = structured_score(text, record)
        row["ocr_score"] = round(score, 4)
        row["ocr_conflicts"] = conflicts
        if fields:
            row["ocr_fields"] = {key: round(value, 4) for key, value in fields.items()}
        base = float(row.get("score") or 0.0)
        row["score"] = round(base + alpha * score - conflict_penalty * conflicts, 4)
    head = _rank(head)
    combined = head + tail
    for rank, row in enumerate(combined, 1):
        row["rank"] = rank
    return combined


def ocr_union(candidates, text, catalog, top_k=10, alpha=0.18):
    scored = []
    for slug, record in catalog.items():
        score, conflicts, fields = structured_score(text, record)
        scored.append((score - 0.25 * conflicts, slug, score, conflicts, fields))
    selected = sorted(scored, key=lambda item: (-item[0], item[1]))[:top_k]
    by_slug = {row["slug"]: dict(row) for row in candidates}
    for _rank_score, slug, score, conflicts, fields in selected:
        row = by_slug.get(slug)
        if row is None:
            row = {"slug": slug, "score": 0.0, "rank": len(by_slug) + 1,
                   "visual_score": None, "candidate_source": "ocr"}
            by_slug[slug] = row
        else:
            row.setdefault("visual_score", row.get("score"))
            row["candidate_source"] = "visual+ocr"
        row["ocr_score"] = round(score, 4)
        row["ocr_conflicts"] = conflicts
        row["ocr_fields"] = {key: round(value, 4) for key, value in fields.items()}
        row["score"] = round(float(row.get("score") or 0.0)
                             + alpha * score - alpha * 0.25 * conflicts, 4)
    return _rank(list(by_slug.values()))


def secondary_union(primary, secondary, primary_weight=0.7, secondary_weight=0.3):
    total = primary_weight + secondary_weight
    by_slug = {}
    for row in primary:
        out = dict(row)
        out["primary_score"] = row.get("score")
        out["secondary_score"] = None
        by_slug[row["slug"]] = out
    for row in secondary:
        out = by_slug.get(row["slug"])
        if out is None:
            out = {"slug": row["slug"], "rank": len(by_slug) + 1,
                   "score": row.get("score"), "visual_score": None,
                   "primary_score": None, "candidate_source": "secondary"}
            by_slug[row["slug"]] = out
        out["secondary_score"] = row.get("score")
    for row in by_slug.values():
        present = []
        if isinstance(row.get("primary_score"), (int, float)):
            present.append((primary_weight, float(row["primary_score"])))
        if isinstance(row.get("secondary_score"), (int, float)):
            present.append((secondary_weight, float(row["secondary_score"])))
        if present:
            denominator = sum(weight for weight, _ in present) or total
            row["score"] = round(sum(weight * value for weight, value in present)
                                 / denominator, 4)
    return _rank(list(by_slug.values()))


def reject(candidates, min_score, score_field="score", min_margin=0.0):
    if not candidates:
        return [], []
    first = candidates[0]
    value = first.get(score_field)
    if not isinstance(value, (int, float)):
        value = first.get("score")
    second = candidates[1].get(score_field) if len(candidates) > 1 else None
    if not isinstance(second, (int, float)) and len(candidates) > 1:
        second = candidates[1].get("score")
    margin = float(value) - float(second) if isinstance(second, (int, float)) else float(value)
    if not isinstance(value, (int, float)) or float(value) < min_score:
        return [], [dict(row) for row in candidates[:5]]
    out = [dict(row) for row in candidates]
    out[0]["decision"] = "found" if margin >= min_margin else "probable"
    out[0]["decision_score"] = round(float(value), 4)
    out[0]["decision_margin"] = round(margin, 4)
    return out, []


class TesseractOCR:
    """Local `rus+eng` OCR with a content-addressed JSON cache."""

    def __init__(self, cache_dir):
        self.command = shutil.which("tesseract")
        if not self.command:
            raise ConfigError("competitor OCR requires the tesseract command")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def __call__(self, path):
        data = Path(path).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        cache = self.cache_dir / f"{digest}.json"
        try:
            value = json.loads(cache.read_text(encoding="utf-8"))
            if value.get("v") == 1 and isinstance(value.get("text"), str):
                return value["text"]
        except (OSError, ValueError):
            pass
        process = subprocess.run(
            [self.command, str(path), "stdout", "-l", "rus+eng", "--psm", "11", "tsv"],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if process.returncode:
            raise RuntimeError("tesseract failed: %s" % process.stderr.strip())
        reader = csv.DictReader(io.StringIO(process.stdout), delimiter="\t")
        words = []
        for row in reader:
            text = (row.get("text") or "").strip()
            try:
                confidence = float(row.get("conf") or -1)
            except ValueError:
                confidence = -1
            if text and confidence >= 0:
                words.append(text)
        text = " ".join(words)
        payload = {"v": 1, "sha256": digest, "text": text}
        temporary = cache.with_name(cache.name + ".tmp.%d.%d" % (os.getpid(), threading.get_ident()))
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with self._lock:
            os.replace(temporary, cache)
        return text


class SiftReranker:
    """Bounded SIFT and RANSAC rerank over prepared catalogue inputs."""

    def __init__(self, embedding_dir):
        try:
            import cv2
        except ImportError as exc:
            raise ConfigError("competitor sift_rerank requires opencv-python-headless") from exc
        self.cv2 = cv2
        self.images = Path(embedding_dir) / embeddings.IMAGES
        self.sift = cv2.SIFT_create(nfeatures=1200)

    def _features(self, path):
        image = self.cv2.imread(str(path), self.cv2.IMREAD_GRAYSCALE)
        if image is None:
            return [], None
        if max(image.shape) > 1200:
            scale = 1200 / max(image.shape)
            image = self.cv2.resize(image, None, fx=scale, fy=scale,
                                    interpolation=self.cv2.INTER_AREA)
        return self.sift.detectAndCompute(image, None)

    def _candidate_path(self, row):
        items = [item for item in row.get("items") or []
                 if item.get("view") == "full" and item.get("sha256")]
        if not items:
            return None
        best = max(items, key=lambda item: item.get("cosine")
                   if isinstance(item.get("cosine"), (int, float)) else -2.0)
        path = self.images / embeddings.image_name(best["sha256"], "full")
        return path if path.is_file() else None

    def __call__(self, query_path, candidates, top_k=5, weight=0.05):
        query_keypoints, query_descriptors = self._features(query_path)
        head, tail = [dict(row) for row in candidates[:top_k]], [dict(row) for row in candidates[top_k:]]
        if query_descriptors is None or len(query_keypoints) < 4:
            return candidates
        matcher = self.cv2.BFMatcher(self.cv2.NORM_L2)
        for row in head:
            target = self._candidate_path(row)
            inliers = good_count = 0
            if target is not None:
                target_keypoints, target_descriptors = self._features(target)
                if target_descriptors is not None and len(target_keypoints) >= 4:
                    pairs = matcher.knnMatch(query_descriptors, target_descriptors, k=2)
                    good = [left for left, right in pairs if left.distance < 0.75 * right.distance]
                    good_count = len(good)
                    if good_count >= 4:
                        import numpy as np
                        source = np.float32([query_keypoints[item.queryIdx].pt for item in good]).reshape(-1, 1, 2)
                        destination = np.float32([target_keypoints[item.trainIdx].pt for item in good]).reshape(-1, 1, 2)
                        _matrix, mask = self.cv2.findHomography(source, destination,
                                                               self.cv2.RANSAC, 5.0)
                        inliers = int(mask.sum()) if mask is not None else 0
            geometry = min(1.0, inliers / 20.0)
            row["sift_matches"] = good_count
            row["sift_inliers"] = inliers
            row["sift_score"] = round(geometry, 4)
            row.setdefault("visual_score", row.get("score"))
            row["score"] = round(float(row.get("score") or 0.0) + weight * geometry, 4)
        combined = _rank(head) + tail
        for position, row in enumerate(combined, 1):
            row["rank"] = position
        return combined


def _append_trace(trace, action, start_ms, elapsed_ms, output):
    value = dict(trace or {}, v=1)
    steps = list(value.get("steps") or [])
    steps.append({"id": "competitor-" + action, "start_ms": round(start_ms, 1),
                  "ms": round(elapsed_ms, 1), "out": output})
    value["steps"] = steps
    return value


class CompetitorSteps:
    """Apply the checked actions after primary embedding retrieval."""

    def __init__(self, inner, options, catalog, top_k=5, secondary=None, ocr=None,
                 sift=None, cache_dir=None):
        self.inner = inner
        self.options = options
        self.catalog = catalog
        self.secondary = secondary
        self.id = inner.id
        self.catalogue = inner.catalogue
        self.top_k = top_k
        self.ocr = ocr
        if self.ocr is None and any(action["action"].startswith("ocr_")
                                    for action in options["actions"]):
            root = cache_dir or Path("work") / "competitor-ocr-cache"
            self.ocr = TesseractOCR(root)
        self.sift = sift
        self.spec = dict(inner.spec)
        self.spec["top_k"] = top_k
        self.spec["competitor"] = options
        if any(action["action"].startswith("ocr_") for action in options["actions"]):
            self.spec["ocr_normalization"] = dict(wine_terms.IDENTITY)

    def ask(self, path, first=None):
        started = time.perf_counter()
        result = self.inner.ask(path, first=first)
        candidates, latency, status, error, trace = result
        if error:
            return candidates, latency, status, error, trace
        candidates = [dict(row) for row in candidates]
        ocr_text = None
        secondary_answer = None
        for action in self.options["actions"]:
            name = action["action"]
            action_started = time.perf_counter()
            output = {}
            try:
                if name == "view_fusion":
                    candidates = view_fusion(candidates, action["weights"])
                elif name == "ocr_rerank":
                    ocr_text = self.ocr(path) if ocr_text is None else ocr_text
                    candidates = ocr_rerank(
                        candidates, ocr_text, self.catalog, action["profile"], action["top_k"],
                        action["alpha"], action["conflict_penalty"],
                    )
                    output["ocr_text"] = ocr_text
                    output["ocr_normalization"] = dict(wine_terms.IDENTITY, text=wine_terms.normalize(ocr_text))
                elif name == "ocr_union":
                    ocr_text = self.ocr(path) if ocr_text is None else ocr_text
                    candidates = ocr_union(candidates, ocr_text, self.catalog,
                                           action["top_k"], action["alpha"])
                    output["ocr_text"] = ocr_text
                    output["ocr_normalization"] = dict(wine_terms.IDENTITY, text=wine_terms.normalize(ocr_text))
                elif name == "secondary_union":
                    if secondary_answer is None:
                        if self.secondary is None:
                            raise RuntimeError("secondary backend is not configured")
                        secondary_answer = self.secondary.ask(path)
                    other, _other_ms, _other_status, other_error, _other_trace = secondary_answer
                    if other_error:
                        raise RuntimeError("secondary backend: " + other_error)
                    candidates = secondary_union(candidates, other,
                                                 action["primary_weight"],
                                                 action["secondary_weight"])
                elif name == "sift_rerank":
                    if self.sift is None:
                        raise RuntimeError("SIFT reranker is not configured")
                    candidates = self.sift(path, candidates, action["top_k"], action["weight"])
                elif name == "reject":
                    candidates, audit = reject(candidates, action["min_score"],
                                               action["score_field"], action["min_margin"])
                    output["rejected"] = audit
                else:  # check_options makes this unreachable.
                    raise RuntimeError("unknown competitor action " + name)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                elapsed = (time.perf_counter() - started) * 1000
                return [], round(elapsed), None, f"competitor {name}: {exc}", trace
            elapsed_ms = (time.perf_counter() - action_started) * 1000
            output["candidates"] = len(candidates)
            output["top"] = [{"slug": row["slug"], "score": row.get("score")}
                             for row in candidates[:5]]
            trace = _append_trace(trace, name, latency, elapsed_ms, output)
            latency += elapsed_ms
        return candidates[:self.top_k], round(latency), status, None, trace
