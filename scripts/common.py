"""Shared state, configuration, and helpers for the svoe-vino testset builder."""
import base64, io, json, os, re, sqlite3, sys, threading, time, urllib.parse

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.yaml")


def load_config(path=CONFIG_PATH):
    """Return the content of `config.yaml`. A missing file gives an empty map."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


CONFIG = load_config()

# Root directory for every relative path of the configuration.
ROOTDIR = CONFIG.get("rootdir") or os.path.dirname(ROOT)


def rootpath(path):
    """Resolve a path against ROOTDIR. An absolute path stays as it is."""
    return path if os.path.isabs(path) else os.path.join(ROOTDIR, path)


def config_path(key, default):
    """Return the configured path of `key`. An absent key gives `default`."""
    value = CONFIG.get(key)
    return rootpath(value) if value else default


# --------------------------------------------------------------- the datasets

# One dataset owns the files and the directories of one photo set: the photos,
# the labels of the reviewer, the variant groups, the excluded slugs, the trash,
# and the runs of the match runner. `config.yaml` holds one entry per dataset
# under the key `dataset`, and each entry holds a `name`.
DATASET_KEYS = ("photo_dir", "trash_dir", "label_file", "variant_groups_file",
                "manual_groups_file", "excluded_slugs_file", "runs_dir")
# The keys that every dataset shares. They stand at the top of `config.yaml`.
GENERIC_KEYS = ("rootdir", "catalog_file", "patch_dir", "bottle_cropped_dir",
                "bottle_label_dir", "bottle_label_box_dir", "backends_file", "clusters")
# The dataset that a script uses when it gets no name.
DEFAULT_DATASET = "default"


class ConfigError(Exception):
    """`config.yaml` cannot be read as it stands."""


def load_datasets(config):
    """Return the datasets of the configuration, as name to entry.

    The function refuses a file with no `dataset` list. Such a file is the old
    flat shape, which held the paths of one photo set at the top level.
    """
    entries = config.get("dataset")
    if not isinstance(entries, list) or not entries:
        stray = sorted(k for k in DATASET_KEYS if k in config)
        note = ("  The key(s) %s stand at the top of the file. Each one belongs "
                "in a dataset entry now." % ", ".join(stray)) if stray else ""
        raise ConfigError(
            "the key `dataset` is missing, or it holds no entry. Every dataset "
            "stands in that list, and each entry holds a `name` and its own "
            "paths.%s" % note)
    out = {}
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ConfigError("entry %d of `dataset` is not a map" % i)
        name = str(entry.get("name") or "").strip()
        if not name:
            raise ConfigError("entry %d of `dataset` holds no `name`" % i)
        if name in out:
            raise ConfigError("two datasets carry the name `%s`" % name)
        bad = sorted(set(entry) - set(DATASET_KEYS) - {"name"})
        if bad:
            raise ConfigError(
                "the dataset `%s` holds the key(s) %s. A dataset holds `name` and "
                "these keys alone: %s. The key(s) %s are the same for every "
                "dataset and stand at the top of the file."
                % (name, ", ".join(bad), ", ".join(DATASET_KEYS),
                   ", ".join(GENERIC_KEYS)))
        out[name] = entry
    if DEFAULT_DATASET not in out:
        raise ConfigError(
            "no dataset carries the name `%s`. A script that runs with no "
            "--dataset uses that name. The file holds: %s."
            % (DEFAULT_DATASET, ", ".join(sorted(out))))
    return out


try:
    DATASETS = load_datasets(CONFIG)
except ConfigError as _exc:
    sys.exit("error in %s: %s" % (CONFIG_PATH, _exc))


def dataset_names():
    """Return the name of every dataset of `config.yaml`, in the order of the file."""
    return list(DATASETS)


# Catalogue of the vino-svoe.ru wines, one JSON record per line. Every dataset
# reads the same catalogue.
CATALOG_FILE = config_path(
    "catalog_file",
    os.path.join(os.path.dirname(ROOT), "svoe-wino-hackaton", "dataset", "derived",
                 "official-2026-09-17", "catalog.jsonl"))

# Corrected catalogue photos, one file per wine slug: `<slug>.<extension>`.
# A patch REPLACES the catalogue photo of that slug. It does not stand beside
# it, because a wrong photo is not a second view of the wine. The catalogue
# file is never rewritten; the patch is a layer above it. Every dataset reads
# the same patches. `svoe-vino-matcher/config.yaml` reads the same directory.
# There is NO default directory: a patch is applied only when `config.yaml`
# asks for it.
PATCH_DIR = config_path("patch_dir", "")

# The file types that count as a patch. The name before the extension is the slug.
PATCH_EXT = (".webp", ".jpg", ".jpeg", ".png", ".gif", ".bmp")


def load_patches(patch_dir=None):
    """Return slug -> path of every corrected catalogue photo.

    An unset `patch_dir` gives an empty map. A configured directory that is not
    on disk is an error, because a typo in the path MUST NOT disable the
    corrections without a word.
    """
    path = PATCH_DIR if patch_dir is None else patch_dir
    if not path:
        return {}
    if not os.path.isdir(path):
        raise ConfigError("patch_dir is not a directory: %s" % path)
    out = {}
    for fn in sorted(os.listdir(path)):
        slug, ext = os.path.splitext(fn)
        full = os.path.join(path, fn)
        if ext.lower() not in PATCH_EXT or not os.path.isfile(full):
            continue
        if slug in out:
            raise ConfigError(
                "%s holds two patches for the slug `%s`: %s and %s. "
                "One slug takes one patch."
                % (path, slug, os.path.basename(out[slug]), fn))
        out[slug] = full
    return out


# Label crops of the catalogue bottle photo, one file per wine slug:
# `<slug>.<extension>`. `svoe-wino-hackaton/scripts/build_labels.py` cuts them
# out with SAM3.
#
# A label crop does NOT replace the catalogue photo. A patch replaces a wrong
# photo; a label crop is a second view of the SAME photo, so the review tool
# shows the package or the label on request. A crop is cut from the patch when
# the wine has one.
#
# `bottle_label_dir` holds the crop with every pixel outside the label mask set
# to white. `bottle_label_box_dir` holds the bounding box crop alone. There is NO
# default directory. An unset key takes the choice out of the review tool.
#
# The key `label_file` of a dataset is a different thing. It holds the labels
# that the reviewer gives to a photo.
BOTTLE_LABEL_DIR = config_path("bottle_label_dir", "")
BOTTLE_LABEL_BOX_DIR = config_path("bottle_label_box_dir", "")


def load_bottle_labels(label_dir):
    """Return slug -> path of every label crop of `label_dir`.

    An unset directory gives an empty map. A configured directory that is not on
    disk is an error, because a typo in the path MUST NOT take the label crops
    away without a word. Two files for one slug cannot happen by construction,
    and the first name in sort order wins if they do.
    """
    if not label_dir:
        return {}
    if not os.path.isdir(label_dir):
        raise ConfigError("the label directory is not a directory: %s" % label_dir)
    out = {}
    for fn in sorted(os.listdir(label_dir)):
        slug, ext = os.path.splitext(fn)
        full = os.path.join(label_dir, fn)
        if ext.lower() not in PATCH_EXT or not os.path.isfile(full):
            continue
        out.setdefault(slug, full)
    return out


# Cropped catalogue photos, one file per wine slug: `<slug>.png`.
# `svoe-wino-hackaton/scripts/build_cropped.py` cuts the empty border away from
# the catalogue photo, or from the patch when the wine has one. The crop holds
# the same pixels as that photo, without the transparent or white border.
#
# The review tool shows the crop in place of the catalogue photo. The stages
# `03_embed.py` and `08_variants.py` embed the crop as the reference. A wine with
# no crop keeps its patch or its catalogue photo. The mark `patched` does not
# change: it still states that the picture comes from a patch.
#
# The pixel checks of the review tool compare a candidate photo with the
# catalogue photo of the delivery, so they keep reading `local_path`.
# There is NO default directory. An unset key shows the photos with their border.
BOTTLE_CROPPED_DIR = config_path("bottle_cropped_dir", "")


def load_cropped_bottles(cropped_dir=None):
    """Return slug -> path of every cropped catalogue photo.

    An unset `bottle_cropped_dir` gives an empty map. A configured directory that
    is not on disk is an error, because a typo in the path MUST NOT bring the
    border back without a word. The directory has the flat layout of the label
    crops, so `load_bottle_labels` reads it.
    """
    path = BOTTLE_CROPPED_DIR if cropped_dir is None else cropped_dir
    if not path:
        return {}
    if not os.path.isdir(path):
        raise ConfigError("bottle_cropped_dir is not a directory: %s" % path)
    return load_bottle_labels(path)


def changed_after(one, other):
    """Answer whether the file `one` changed after the file `other`."""
    try:
        return os.path.getmtime(one) > os.path.getmtime(other)
    except OSError:
        return False


def catalogue_picture(slug, record, crops, patches):
    """Return the catalogue picture of `slug` for display and embedding, or None.

    The crop wins over the patch, and the patch wins over the photo of the
    catalogue record. A patch is a correction of that record, so no view may
    show the photo it corrects. A crop is the same picture as the patch or the
    record, with its empty border cut away.

    A patch that changed after its crop wins over the crop. Such a crop was cut
    from the picture before the correction. Run
    `svoe-wino-hackaton/scripts/build_cropped.py` again to crop the new patch.
    """
    crop = crops.get(slug)
    patch = patches.get(slug)
    if crop and not (patch and changed_after(patch, crop)):
        return crop
    if patch:
        return patch
    return (record or {}).get("local_path")


# Match backends. `scripts/match_run.py` reads this file.
BACKENDS_FILE = config_path("backends_file", os.path.join(ROOT, "backends.yaml"))

# Catalogue clusters. `scripts/10_clusters.py` reads the settings of this block and
# writes `file`. The page `/clusters` of the review tool reads `file`. The block is
# the same for every dataset, because a cluster is a group of catalogue cards.
CLUSTERS = CONFIG.get("clusters") or {}
CLUSTERS_FILE = (rootpath(CLUSTERS["file"]) if CLUSTERS.get("file")
                 else os.path.join(ROOT, "dataset", "catalog-clusters.json"))

# The name of the dataset in use. `select_dataset` sets it.
DATASET = None
# The paths of that dataset. `select_dataset` sets each one.
PHOTO_DIR = TRASH_DIR = LABEL_FILE = None
VARIANT_GROUPS_FILE = MANUAL_GROUPS_FILE = EXCLUDED_SLUGS_FILE = RUNS_DIR = None
OUT = None
# Every configured path, in the order of the report that a script prints at start.
CONFIG_PATHS = ()


def select_dataset(name=None):
    """Bind the paths of one dataset and return its name.

    A script that reads a path at call time needs no more than this call. A script
    that binds a path of `common` at import time MUST bind it again after this
    call, because this function rebinds the names of `common` alone.

    The name `None` selects `DEFAULT_DATASET`.
    """
    global DATASET, PHOTO_DIR, TRASH_DIR, LABEL_FILE, VARIANT_GROUPS_FILE
    global MANUAL_GROUPS_FILE, EXCLUDED_SLUGS_FILE, RUNS_DIR, OUT, CONFIG_PATHS
    name = name or DEFAULT_DATASET
    if name not in DATASETS:
        raise ConfigError("unknown dataset `%s`. %s holds: %s."
                          % (name, os.path.basename(CONFIG_PATH),
                             ", ".join(dataset_names())))
    entry = DATASETS[name]

    def path(key, default):
        value = entry.get(key)
        return rootpath(value) if value else default

    DATASET = name
    # Photo set. One directory per wine slug.
    PHOTO_DIR = path("photo_dir", os.path.join(ROOT, "my"))
    # A deleted photo is moved here, not unlinked.
    TRASH_DIR = path("trash_dir", os.path.join(ROOT, "work", "trash"))
    # Labels of the review tool.
    LABEL_FILE = path("label_file", os.path.join(ROOT, "review-labels.json"))
    # Variant groups. `scripts/08_variants.py` writes this file.
    VARIANT_GROUPS_FILE = path("variant_groups_file",
                               os.path.join(ROOT, "derived", "variant-groups.json"))
    # Manual variant pairs. The review tool writes this file. `scripts/08_variants.py`
    # never writes it, so a new run of that script keeps the hand-made pairs.
    MANUAL_GROUPS_FILE = path("manual_groups_file",
                              os.path.join(ROOT, "my", "manual-groups.json"))
    # Excluded slugs. The photos of an excluded slug MUST NOT be used for benchmarking.
    EXCLUDED_SLUGS_FILE = path("excluded_slugs_file",
                               os.path.join(ROOT, "excluded-slugs.json"))
    # One directory per match run.
    RUNS_DIR = path("runs_dir", os.path.join(ROOT, "runs"))
    # The pipeline writes the photos it downloads into the photo set of the dataset.
    OUT = PHOTO_DIR
    CONFIG_PATHS = (
        ("catalog_file", CATALOG_FILE),
        # `patch_dir` is optional, so it is reported only when it is configured.
    ) + ((("patch_dir", PATCH_DIR),) if PATCH_DIR else ()
         ) + ((("bottle_cropped_dir", BOTTLE_CROPPED_DIR),) if BOTTLE_CROPPED_DIR else ()
         ) + ((("bottle_label_dir", BOTTLE_LABEL_DIR),) if BOTTLE_LABEL_DIR else ()
         ) + ((("bottle_label_box_dir", BOTTLE_LABEL_BOX_DIR),) if BOTTLE_LABEL_BOX_DIR else ()) + (
        ("photo_dir", PHOTO_DIR),
        ("trash_dir", TRASH_DIR),
        ("label_file", LABEL_FILE),
        ("variant_groups_file", VARIANT_GROUPS_FILE),
        ("manual_groups_file", MANUAL_GROUPS_FILE),
        ("excluded_slugs_file", EXCLUDED_SLUGS_FILE),
        ("backends_file", BACKENDS_FILE),
        ("clusters_file", CLUSTERS_FILE),
        ("runs_dir", RUNS_DIR),
    )
    return name


# A script that never asks for a dataset works with the default one.
select_dataset()


def print_config(keys=None, stream=None):
    """Print the configuration that the script starts with, and the work directory."""
    out = stream or sys.stdout
    pairs = [(k, v) for k, v in CONFIG_PATHS if keys is None or k in keys]
    width = max([len(k) for k, _ in pairs] + [len("rootdir"), len("dataset")])
    print("configuration: %s" % CONFIG_PATH, file=out)
    print("  %-*s : %s%s" % (width, "dataset", DATASET,
                             "" if len(DATASETS) < 2 else
                             "   (of %d: %s)" % (len(DATASETS),
                                                 ", ".join(dataset_names()))),
          file=out)
    print("  %-*s : %s" % (width, "rootdir", ROOTDIR), file=out)
    for key, value in pairs:
        mark = "" if os.path.exists(value) else "   (absent)"
        print("  %-*s : %s%s" % (width, key, value, mark), file=out)
    print("work directory: %s" % os.getcwd(), file=out)


WORK = os.path.join(ROOT, "work")
RAW = os.path.join(WORK, "raw")
DB_PATH = os.path.join(WORK, "state.db")

WINES_JSONL = ("/Volumes/Storage/Datasets/2026_LCT_Hackatons/"
               "10-Сканер_российских_вин/"
               "vino-svoe.ru/wines.jsonl")

GX10 = "http://192.168.86.14:18081"
EMBED_MODEL = "siglip2"
VLM_MODEL = "qwen3-vl-32b"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

# Hosts that publish catalogue renders only. A non-studio photo never comes from them.
STUDIO_HOSTS = {
    "simplewine.ru", "static.simplewine.ru", "luding.ru", "cdn.metro-cc.ru", "metro-cc.ru",
    "alcoplaza.ru", "www.alcoplaza.ru", "cigarpro.ru", "www.cigarpro.ru", "wine.style",
    "s2.wine.style", "s1.wine.style", "winestyle.ru", "www.winestyle.ru", "cru.ru", "www.cru.ru",
    "bestwine24.ru", "winestreet.ru", "static.winestreet.ru", "lf-wines.ru", "garryspirit.ru",
    "img.wine-shopper.ru", "wine-shopper.ru", "main-cdn.sbermegamarket.ru", "images.av.ru",
    "static.decanter.ru", "decanter.ru", "ladogawine.ru", "krasnostop.ru", "m2-shop.ru",
    "www.m2-shop.ru", "winestore71.ru", "vinotheque.ru", "krymwine.ru", "chateau-pinot.ru",
    "imgproxy.kuper.ru", "www.auchan.ru", "auchan.ru", "aromatnyimir.ru", "www.aromatnyimir.ru",
    "magnit.ru", "lenta.com", "5ka.ru", "perekrestok.ru", "vkusvill.ru", "api.vino-svoe.ru",
    "vino-svoe.ru", "swn.ru", "rskrf.ru", "static.tildacdn.com", "img.magnific.com",
    "winelab.ru", "www.winelab.ru", "amwine.ru", "www.amwine.ru", "alkoteka.com",
    "www.alkoteka.com", "fix-price.com", "sbermarket.ru", "eda.yandex.ru",
}

# Hosts whose images are user-generated. These carry the real-world photos.
UGC_HOST_PATTERNS = (
    "irecommend", "otzovik", "vivino", "pinimg", "userapi", "vk.com", "vkuser",
    "wbbasket", "wildberries", "ozone.ru", "ozon.ru", "ozonusercontent", "avatars.mds.yandex.net",
    "avito", "2gis", "flamp", "tripadvisor", "restoclub", "instagram", "fbcdn",
    "livejournal", "drive2", "pikabu", "yaplakal", "forum", "blogspot", "wordpress",
    "telegra.ph", "tgstat", "cdn-irec",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS wines (
  slug TEXT PRIMARY KEY,
  title TEXT, producer TEXT, category TEXT, region TEXT,
  ref_path TEXT, page_url TEXT,
  searched INTEGER DEFAULT 0,
  downloaded INTEGER DEFAULT 0,
  embedded INTEGER DEFAULT 0,
  verified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL,
  url TEXT NOT NULL,
  host TEXT,
  engine TEXT,
  query TEXT,
  page_url TEXT,
  title TEXT,
  ugc INTEGER DEFAULT 0,
  dl_status TEXT,
  local_path TEXT,
  sha256 TEXT,
  width INTEGER, height INTEGER, bytes INTEGER,
  sim REAL,
  bg_white REAL,
  vlm_same INTEGER,
  vlm_conf REAL,
  vlm_studio INTEGER,
  vlm_front INTEGER,
  vlm_raw TEXT,
  selected INTEGER DEFAULT 0,
  UNIQUE(slug, url)
);
CREATE INDEX IF NOT EXISTS idx_cand_slug ON candidates(slug);
CREATE INDEX IF NOT EXISTS idx_cand_dl ON candidates(dl_status);
CREATE TABLE IF NOT EXISTS queries (
  slug TEXT, engine TEXT, query TEXT, n INTEGER, err TEXT, ts REAL,
  PRIMARY KEY (slug, engine, query)
);
"""

_local = threading.local()


def db():
    if getattr(_local, "conn", None) is None:
        os.makedirs(WORK, exist_ok=True)
        c = sqlite3.connect(DB_PATH, timeout=120)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.executescript(SCHEMA)
        _local.conn = c
    return _local.conn


def host_of(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""


def is_studio_host(host):
    h = host.lower()
    if h in STUDIO_HOSTS:
        return True
    base = h[4:] if h.startswith("www.") else h
    return base in STUDIO_HOSTS


def is_ugc_host(host):
    h = host.lower()
    return any(p in h for p in UGC_HOST_PATTERNS)


def load_wines():
    rows = []
    with open(WINES_JSONL, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            rows.append({
                "slug": r["slug"],
                "title": (r.get("title") or "").strip(),
                "producer": ((r.get("manufacturer") or {}).get("name") or "").strip(),
                "category": ((r.get("category") or {}).get("name") or "").strip(),
                "region": ((r.get("region") or {}).get("name") or "").strip(),
                "ref_path": (r.get("image") or {}).get("local_path") or "",
                "page_url": r.get("page_url") or "",
            })
    return rows


def init_wines():
    conn = db()
    rows = load_wines()
    conn.executemany(
        "INSERT OR IGNORE INTO wines (slug,title,producer,category,region,ref_path,page_url)"
        " VALUES (:slug,:title,:producer,:category,:region,:ref_path,:page_url)", rows)
    conn.commit()
    return len(rows)


def data_url(path, maxside=None, quality=88):
    """Return a JPEG data URL. Downscale when maxside is given."""
    from PIL import Image
    if maxside is None:
        ext = os.path.splitext(path)[1].lstrip(".").lower()
        ext = {"jpg": "jpeg"}.get(ext, ext)
        if ext in ("jpeg", "png", "gif"):
            with open(path, "rb") as fh:
                return "data:image/%s;base64,%s" % (ext, base64.b64encode(fh.read()).decode())
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
        im = bg
    else:
        im = im.convert("RGB")
    if maxside:
        im.thumbnail((maxside, maxside))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def post_json(path, payload, timeout=900, retries=3):
    import urllib.request, urllib.error
    body = json.dumps(payload).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(GX10 + path, data=body,
                                         headers={"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (attempt + 1))
    raise last


def slug_dir(base, slug):
    d = os.path.join(base, slug)
    os.makedirs(d, exist_ok=True)
    return d


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)
