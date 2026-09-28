"""Read one standalone embedding bundle.

The workbench script `build_matcher_bundle.py` writes the bundle, and
`validate_matcher_bundle.py` checks its full contract. The matcher reads only the bundle
files. It imports no workbench code.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np


FORMAT = "svoe-vino-matcher-bundle"
FORMAT_VERSION = 1
SCORING = {"similarity": "dot_product", "item_reduction": "max", "view_reduction": "mean"}
MANIFEST = "manifest.json"
VECTORS = "vectors.npy"
CANDIDATES = "candidates.jsonl"


class BundleError(ValueError):
    """The bundle is missing or does not satisfy the bundle contract."""


@dataclass(frozen=True, eq=False)
class Bundle:
    """The catalogue vectors of one bundle, one matrix row per candidate relation.

    `views[view]` holds the matrix of the view and the wine number of each row.
    `slugs` is sorted, so the smallest wine number is the smallest slug.
    """

    path: Path
    embedding: dict
    dimension: int
    slugs: tuple[str, ...]
    views: dict

    def top1(self, view, query):
        """Return the slug and the cosine of the wine with the best cosine in `view`.

        `query` is one L2-normalized vector. Equal cosines go to the smallest slug.
        """
        matrix, wines = self.views[view]
        best = np.full(len(self.slugs), -np.inf, dtype=np.float32)
        np.maximum.at(best, wines, matrix @ query)
        number = int(np.argmax(best))
        return self.slugs[number], float(best[number])


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
    if (manifest.get("format") != FORMAT
            or manifest.get("format_version") != FORMAT_VERSION):
        raise BundleError("unsupported bundle format: %r version %r"
                          % (manifest.get("format"), manifest.get("format_version")))
    if manifest.get("scoring") != SCORING:
        raise BundleError("unsupported bundle scoring: %r" % manifest.get("scoring"))
    embedding = manifest.get("embedding")
    if not isinstance(embedding, dict):
        raise BundleError("manifest.embedding MUST be an object")
    for name in (VECTORS, CANDIDATES):
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
    return Bundle(path=root, embedding=embedding, dimension=int(vectors.shape[1]),
                  slugs=slugs, views=views)
