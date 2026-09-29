"""Read one standalone embedding bundle.

The workbench script `build_matcher_bundle.py` writes the bundle, and
`validate_matcher_bundle.py` checks its full contract. The matcher reads only the bundle
files. It imports no workbench code.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

import numpy as np


FORMAT = "svoe-vino-matcher-bundle"
# Version 2 adds the wine cards to `wines.jsonl`. A version 1 bundle has no cards.
# Version 3 (workbench plan 82) holds the rotated rows of an entry with `rotation_step`:
# one vector row for each angle of an image, and the angle of each row in `items.jsonl`.
FORMAT_VERSIONS = (1, 2, 3)
SCORING = {"similarity": "dot_product", "item_reduction": "max", "view_reduction": "mean"}
MANIFEST = "manifest.json"
VECTORS = "vectors.npy"
ITEMS = "items.jsonl"
CANDIDATES = "candidates.jsonl"
WINES = "wines.jsonl"
# The card fields of a version 2 wine record, in the order of the `/v1/match` answer.
CARD_FIELDS = ("name", "page_url", "producer", "category", "region", "color", "grapes",
               "image_url", "qr_urls")
# The sugar rules of telegram-bot/src/chto_za_vino_bot/catalog.py. The first match wins.
SUGAR_RULES = (
    ("Экстра-брют", r"\b(?:extra|ekstra|экстра)\s+(?:brut|bryut|брют)\b"),
    ("Полусухое", r"\b(?:polusuhoe|полусух\w*|semi\s+dry|demi\s+sec)\b"),
    ("Полусладкое", r"\b(?:polu?s?sladkoe|полуслад\w*|semi\s+sweet)\b"),
    ("Брют", r"\b(?:brut|bryut|брют)\b"),
    ("Сухое", r"\b(?:suhoe|сухое|dry)\b"),
    ("Сладкое", r"\b(?:sladkoe|сладкое|sweet|dolce|doux)\b"),
)


class BundleError(ValueError):
    """The bundle is missing or does not satisfy the bundle contract."""


@dataclass(frozen=True, eq=False)
class Bundle:
    """The catalogue vectors of one bundle, one matrix row per candidate relation.

    `views[view]` holds the matrix of the view and the wine number of each row.
    `slugs` is sorted, so the smallest wine number is the smallest slug. A wine scores the
    best cosine of its rows, so the rotated rows of a version 3 bundle give the maximum
    over the rotation. `angles[view]` holds the angle of each row of that view (version 3,
    or a catalogue index with rotated rows), else None; a later feature MAY use it to
    detect the angle of a candidate bottle.
    """

    path: Path
    embedding: dict
    dimension: int
    slugs: tuple[str, ...]
    views: dict
    # slug -> the wine card of a version 2 bundle, or None for a version 1 bundle.
    cards: dict | None = None
    # view -> the angle of each matrix row (int16), or None with no rotated rows.
    angles: dict | None = None

    def top1(self, view, query):
        """Return the slug and the cosine of the wine with the best cosine in `view`.

        `query` is one L2-normalized vector. Equal cosines go to the smallest slug.
        """
        matrix, wines = self.views[view]
        best = np.full(len(self.slugs), -np.inf, dtype=np.float32)
        np.maximum.at(best, wines, matrix @ query)
        number = int(np.argmax(best))
        return self.slugs[number], float(best[number])

    def ranked(self, view, query):
        """Return `(slug, cosine)` of each wine of `view`, the best cosine first.

        The scores are the scores of `top1`, and equal cosines go to the smallest slug.
        So the first pair is the answer of `top1`. A wine without a vector in `view` is
        not in the list.
        """
        matrix, wines = self.views[view]
        best = np.full(len(self.slugs), -np.inf, dtype=np.float32)
        np.maximum.at(best, wines, matrix @ query)
        order = np.argsort(-best, kind="stable")
        return [(self.slugs[number], float(best[number]))
                for number in order if np.isfinite(best[number])]


def infer_sugar(slug, name):
    """Return the sugar class that the slug or the name states, or None."""
    value = re.sub(r"[^0-9a-zа-яё]+", " ", ("%s %s" % (slug, name)).lower())
    for label, pattern in SUGAR_RULES:
        if re.search(pattern, value):
            return label
    return None


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _check_payload(root, manifest, name):
    recorded = (manifest.get("files") or {}).get(name)
    if not isinstance(recorded, dict):
        raise BundleError("manifest.files does not name %s" % name)
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise BundleError("the payload %s is not a regular file" % name)
    if (path.stat().st_size != recorded.get("bytes")
            or _sha256(path) != recorded.get("sha256")):
        raise BundleError("the payload %s does not match its SHA-256 or byte size" % name)


def load_bundle(directory):
    """Load and check one bundle. Raise BundleError."""
    root = Path(directory)
    if not root.is_dir():
        raise BundleError("the bundle is not a directory: %s" % root)
    try:
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError("cannot read %s: %s" % (root / MANIFEST, exc)) from exc
    if not isinstance(manifest, dict):
        raise BundleError("%s MUST hold a JSON object" % MANIFEST)
    version = manifest.get("format_version")
    if (manifest.get("format") != FORMAT or isinstance(version, bool)
            or version not in FORMAT_VERSIONS):
        raise BundleError("unsupported bundle format: %r version %r"
                          % (manifest.get("format"), manifest.get("format_version")))
    if manifest.get("scoring") != SCORING:
        raise BundleError("unsupported bundle scoring: %r" % manifest.get("scoring"))
    embedding = manifest.get("embedding")
    if not isinstance(embedding, dict):
        raise BundleError("manifest.embedding MUST be an object")
    for name in (VECTORS, CANDIDATES) + ((WINES,) if version >= 2 else ()):
        _check_payload(root, manifest, name)

    try:
        vectors = np.load(root / VECTORS, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise BundleError("cannot load %s: %s" % (VECTORS, exc)) from exc
    shape = (manifest.get("vectors") or {}).get("shape")
    if (vectors.dtype != np.float32 or vectors.ndim != 2
            or list(vectors.shape) != shape):
        raise BundleError("%s does not match the declared float32 shape %r"
                          % (VECTORS, shape))

    angle_of = _read_angles(root, manifest, len(vectors)) if version >= 3 else None
    rows = {}
    try:
        with open(root / CANDIDATES, encoding="utf-8") as source:
            for number, line in enumerate(source, 1):
                candidate = json.loads(line)
                row, slug, view = (candidate["vector_row"], candidate["wine_slug"],
                                   candidate["view"])
                if (isinstance(row, bool) or not isinstance(row, int)
                        or not 0 <= row < len(vectors)):
                    raise BundleError("%s line %d has an invalid vector_row"
                                      % (CANDIDATES, number))
                if not isinstance(slug, str) or not slug or not isinstance(view, str):
                    raise BundleError("%s line %d has an invalid wine_slug or view"
                                      % (CANDIDATES, number))
                rows.setdefault(view, []).append((row, slug))
    except BundleError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BundleError("cannot read %s: %s" % (CANDIDATES, exc)) from exc

    slugs = tuple(sorted({slug for pairs in rows.values() for _, slug in pairs}))
    numbers = {slug: number for number, slug in enumerate(slugs)}
    views = {
        view: (np.ascontiguousarray(vectors[[row for row, _ in pairs]]),
               np.asarray([numbers[slug] for _, slug in pairs], dtype=np.int64))
        for view, pairs in rows.items()
    }
    cards = _read_cards(root) if version >= 2 else None
    angles = None
    if angle_of is not None:
        angles = {view: np.asarray([angle_of[row] for row, _ in pairs], dtype=np.int16)
                  for view, pairs in rows.items()}
    return Bundle(path=root, embedding=embedding, dimension=int(vectors.shape[1]),
                  slugs=slugs, views=views, cards=cards, angles=angles)


def _read_angles(root, manifest, count):
    """Return the angle of each vector row of a version 3 bundle, from `items.jsonl`."""
    _check_payload(root, manifest, ITEMS)
    angle_of = [None] * count
    try:
        with open(root / ITEMS, encoding="utf-8") as source:
            for number, line in enumerate(source, 1):
                item = json.loads(line)
                row, angle = item["vector_row"], item["angle"]
                if (isinstance(row, bool) or not isinstance(row, int) or not 0 <= row < count
                        or isinstance(angle, bool) or not isinstance(angle, int)
                        or not 0 <= angle < 360 or angle_of[row] is not None):
                    raise BundleError("%s line %d has an invalid vector_row or angle"
                                      % (ITEMS, number))
                angle_of[row] = angle
    except BundleError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BundleError("cannot read %s: %s" % (ITEMS, exc)) from exc
    if any(angle is None for angle in angle_of):
        raise BundleError("%s has no angle for each vector row" % ITEMS)
    return angle_of


def _read_cards(root):
    """Return slug -> card of `wines.jsonl`. The card adds the inferred `sugar`."""
    cards = {}
    try:
        with open(root / WINES, encoding="utf-8") as source:
            for number, line in enumerate(source, 1):
                wine = json.loads(line)
                slug = wine["wine_slug"]
                if (not isinstance(slug, str) or not slug
                        or not isinstance(wine["name"], str)
                        or not isinstance(wine["page_url"], str)
                        or not isinstance(wine["qr_urls"], list)):
                    raise BundleError("%s line %d is not a valid wine card" % (WINES, number))
                card = {key: wine[key] for key in CARD_FIELDS}
                card["sugar"] = infer_sugar(slug, wine["name"])
                cards[slug] = card
    except BundleError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BundleError("cannot read %s: %s" % (WINES, exc)) from exc
    return cards
