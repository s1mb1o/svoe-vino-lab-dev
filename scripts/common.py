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


# Catalogue of the vino-svoe.ru wines, one JSON record per line.
CATALOG_FILE = config_path(
    "catalog_file",
    os.path.join(os.path.dirname(ROOT), "svoe-wino-hackaton", "derived", "catalog.jsonl"))

# Photo set. One directory per wine slug.
PHOTO_DIR = config_path("photo_dir", os.path.join(ROOT, "my"))

# A deleted photo is moved here, not unlinked.
TRASH_DIR = config_path("trash_dir", os.path.join(ROOT, "work", "trash"))

# Labels of the review tool.
LABEL_FILE = config_path("label_file", os.path.join(ROOT, "review-labels.json"))

# Variant groups. `scripts/08_variants.py` writes this file.
VARIANT_GROUPS_FILE = config_path(
    "variant_groups_file", os.path.join(ROOT, "derived", "variant-groups.json"))

# Excluded slugs. The photos of an excluded slug MUST NOT be used for benchmarking.
EXCLUDED_SLUGS_FILE = config_path(
    "excluded_slugs_file", os.path.join(ROOT, "excluded-slugs.json"))

# Every configured path, in the order of the report that a script prints at start.
CONFIG_PATHS = (
    ("catalog_file", CATALOG_FILE),
    ("photo_dir", PHOTO_DIR),
    ("trash_dir", TRASH_DIR),
    ("label_file", LABEL_FILE),
    ("variant_groups_file", VARIANT_GROUPS_FILE),
    ("excluded_slugs_file", EXCLUDED_SLUGS_FILE),
)


def print_config(keys=None, stream=None):
    """Print the configuration that the script starts with, and the work directory."""
    out = stream or sys.stdout
    pairs = [(k, v) for k, v in CONFIG_PATHS if keys is None or k in keys]
    width = max([len(k) for k, _ in pairs] + [len("rootdir")])
    print("configuration: %s" % CONFIG_PATH, file=out)
    print("  %-*s : %s" % (width, "rootdir", ROOTDIR), file=out)
    for key, value in pairs:
        mark = "" if os.path.exists(value) else "   (absent)"
        print("  %-*s : %s%s" % (width, key, value, mark), file=out)
    print("work directory: %s" % os.getcwd(), file=out)


WORK = os.path.join(ROOT, "work")
RAW = os.path.join(WORK, "raw")
OUT = PHOTO_DIR
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
