"""The label rules of the catalogue clusters.

Read `docs/plans/05_cluster-label-rules.md` and
`docs/plans/06_label-only-cluster-rules.md`. The terms of these plans are the terms
of this module.

Stage 1 asks the VLM to describe the label of one card. The call sends the
catalogue picture and no card data, so the description holds what the model sees.

Stage 2 asks the VLM where the labels of one cluster differ. The call sends the
label crop of each card of the cluster, the card data, the label descriptions, and
the note of the reviewer. Some catalogue pictures are drawings, and a drawing shows
only the label correctly, so stage 2 uses features of the label only. The answer is a
difference sheet, which holds questions with the expected answer of each card, and a
rule text. The code checks the sheet and sets the mode of the cluster rule:

    sheet    at least one question separates two cards
    verdict  no question separates two cards, and the rule text is not empty and
             names no feature outside the label
    none     neither

Two files hold the results. `scripts/11_cluster_rules.py` and the review tool write
the rules file. Only the review tool writes the notes file. The re-rank kind
`cluster_rules` of `svoe-vino-matcher` reads the rules file.
"""
import base64
import collections
import contextlib
import fcntl
import hashlib
import io
import json
import math
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

import common

# The cache of the model calls is in `pipeline/`. The directory goes to the end of the
# path, so each module of `scripts/` keeps its name. Read docs/plans/25_model-call-cache.md.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "pipeline"))
import model_cache  # noqa: E402

CFG = common.CONFIG.get("cluster_rules") or {}


def _path(key, default_name):
    value = CFG.get(key)
    return common.rootpath(value) if value else os.path.join(common.ROOT, "dataset", default_name)


RULES_FILE = _path("rules_file", "catalog-cluster-rules.json")
NOTES_FILE = _path("notes_file", "catalog-cluster-notes.json")

URL = CFG.get("url") or common.GX10 + "/v1/chat/completions"
MODEL = CFG.get("model") or "qwen3.5-9b"
THINKING = bool(CFG.get("thinking", False))
# Stage 1 scales the picture to this long side, UP or down. A small catalogue
# photo hides small print: at 312 x 1000 pixels the model read «урож. 2024» as
# 2021, and ФАНТОМ as PHANTOM; at a long side of 2048 it read both right.
DESCRIBE_SIDE = int(CFG.get("describe_side", 2048))
RULES_MAX_SIDE = int(CFG.get("rules_max_side", 768))
TIMEOUT_S = float(CFG.get("timeout_s", 300))

# Stage 2 runs once, so it MAY use a more capable model than stage 1. On 2026-09-23
# the owner chose `qwen3.8-max` of the QwenCloud Token Plan, with thinking. The key
# comes from the environment variable that `rules_key_env` names. It is never written
# to a file. `rules_api: qwencloud` sends `enable_thinking` as a top field; the
# llama.cpp gateway reads it from `chat_template_kwargs`.
RULES_URL = CFG.get("rules_url") or URL
RULES_MODEL = CFG.get("rules_model") or MODEL
RULES_API = CFG.get("rules_api") or "llama.cpp"
RULES_KEY_ENV = CFG.get("rules_key_env") or ""
RULES_THINKING = bool(CFG.get("rules_thinking", THINKING))
RULES_WORKERS = max(1, int(CFG.get("rules_workers", 1)))
RULES_TIMEOUT_S = float(CFG.get("rules_timeout_s", 900))

DESCRIBE_MAX_TOKENS = 1500
# With thinking, the reasoning shares the budget of the answer.
RULES_MAX_TOKENS = 16000 if RULES_THINKING else 2500
# A second attempt for an answer that reached `max_tokens`. With temperature 0 the
# same request loops again: on 2026-09-23 one description ran into the limit of 1,500
# tokens in 45 s. The second attempt adds a repeat penalty and a higher limit.
LOOP_GUARD = {"repeat_penalty": 1.15, "max_tokens": 3000}
# The context of the model is 32,768 tokens. The budget keeps room for the answer.
TOKEN_BUDGET = 26000
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# The prompts are sent as they are written here. Do not translate them.
DESCRIBE_PROMPT = (
    "This is a catalogue photo of one wine bottle. Describe its label, so that a person "
    "can tell this bottle apart from similar bottles of the same producer.\n"
    "Report only what you see. Do not guess. If a text or a number is too small to read, "
    "write \"unreadable\" for it.\n"
    "Write each text exactly as it is printed, in its own alphabet. Do not translate it "
    "and do not transliterate it.\n"
    "Answer with one JSON object with these keys:\n"
    "\"texts\": a list of every text that you can read, each as "
    "{\"text\": \"...\", \"where\": \"...\"};\n"
    "\"numbers\": a list of every number that you can read, such as a year, a ratio or a "
    "percentage, each as {\"value\": \"...\", \"where\": \"...\"};\n"
    "\"vintage\": the vintage year if the label shows one, else null;\n"
    "\"colours\": the main colours of the label;\n"
    "\"design\": a short description of the design and the layout of the label;\n"
    "\"marks\": a list of stickers, medals, seals and other marks, each with its place;\n"
    "\"bottle\": the colour and the shape of the bottle and of the capsule."
)

RULES_PROMPT = (
    "You see the label pictures of %(n)d wine cards, Card A to Card %(last)s. Each "
    "picture shows the label of the catalogue picture of one card. "
    "A recognizer confuses these cards, because their bottles look alike. Some "
    "catalogue pictures are drawings, not photos. In a drawing, only the label is "
    "drawn correctly.\n\n"
    "The catalogue data and the label description of each card:\n\n%(cards)s\n\n"
    "Notes of the reviewer about these cards:\n%(notes)s\n\n"
    "Task: find the features of the label that tell the cards apart. Later, a "
    "model will look at the label of a customer photo of ONE of these bottles and "
    "answer your questions. That model sees only the label. The answers MUST identify "
    "the card.\n\n"
    "Rules:\n"
    "1. Write 1 to 3 short questions about the label. A person MUST be able to answer "
    "each question by looking at the label alone.\n"
    "1a. Use only features that are printed on the label. Do not ask about the glass, "
    "the colour of the liquid, the capsule, the cork or the shape of the bottle.\n"
    "2. Use only MAJOR differences between the wines: the grape varieties, a kosher "
    "mark, the wine name or the name of the line, the colour of the wine as the label "
    "states it (red, white, rose, orange), the sugar level (brut, extra brut, dry, "
    "semi-dry, semi-sweet, sweet), a blend ratio, a reserve or special edition mark, "
    "the volume of the bottle, and the vintage year under rule 2a. A different design, "
    "colour shade, background, font or pattern is NOT a major difference. Do not use "
    "it, unless the notes of the reviewer name it.\n"
    "2a. Ask about the vintage year only when the catalogue names of at least two cards "
    "state two different years. Take the expected year of each card from its name, and "
    "give null to a card whose name states no year. A year that only the picture shows "
    "is not a feature of the card, because the next bottle of the same wine can show "
    "the next vintage.\n"
    "3. For each question, give the expected answer of each card as a short text, such "
    "as \"2019\", \"30/70\" or \"brut\". Give null when the label of the card does "
    "not show this feature. Write a name, a grape variety or another text exactly as "
    "the label prints it, in its own alphabet. Do not translate it and do not "
    "transliterate it. When the picture of a card is the picture of another card, "
    "write the text as the catalogue data of the card writes it. Give a sugar level or "
    "a colour of the wine with the words of rule 2.\n"
    "3a. A mark that only some cards carry, such as a kosher mark or a reserve mark, "
    "gets a yes/no question, for example \"Does the label show a kosher mark?\". Give "
    "\"yes\" or \"no\" for each card, and not null.\n"
    "4. Use a question only when at least two cards have different answers.\n"
    "5. The notes of the reviewer are correct. Use them first.\n"
    "6. Do not use a bottle number, a batch number, a lot number or a serial number, "
    "such as «Бут. №» or «Тираж». These numbers change from bottle to bottle.\n"
    "7. The catalogue data is correct. A catalogue picture can be too small to show a "
    "small text. Then take the value from the catalogue data, for example a year, a "
    "grape or a ratio in the name.\n"
    "8. A model wrote the label descriptions, and they can hold errors. Use a feature "
    "only when you see it in the pictures, or when the catalogue data or the notes of "
    "the reviewer state it.\n"
    "9. Two texts that differ only by their alphabet, such as ФАНТОМ and PHANTOM, are "
    "the same text and are not a difference.\n"
    "10. The alcohol value can change between two vintages of one wine. Use it only "
    "when no other feature differs.\n"
    "11. List the groups of cards that no major feature tells apart in "
    "\"indistinguishable\".\n"
    "12. Also write the rule as one short plain text, for example: \"If the label shows "
    "30/70, it is card A; otherwise it is card B.\"\n\n"
    "Answer with one JSON object:\n"
    "{\"differences\": \"where the labels differ\", \"questions\": [{\"question\": "
    "\"...\", \"answers\": {\"A\": \"...\", \"B\": null}}], \"rule\": \"...\", "
    "\"indistinguishable\": [[\"A\", \"B\"]]}"
)

CARD_BLOCK = (
    "Card %(letter)s: name \"%(name)s\"; producer \"%(producer)s\"; category "
    "\"%(category)s\"; grapes \"%(grapes)s\"; alcohol %(alcohol)s (the number at the "
    "end of the catalogue slug).\n"
    "Label description of card %(letter)s: %(description)s"
)

# The caption before the picture of each card in stage 2. The catalogue reuses the
# picture of one card for another card: on 2026-09-24, 43 cards of 21 clusters shared
# a picture with another card of their cluster. The label crop then shows the label of
# one card only, and the model took that label for both cards. The caption names the
# cards that share the picture.
CAPTION = "Card %(letter)s:"
CAPTION_NO_LABEL = ("Card %(letter)s (the whole catalogue picture, because no label crop "
                    "exists):")
CAPTION_SHARED = ("Card %(letter)s (the same catalogue picture as card %(twins)s. The "
                  "catalogue can reuse the picture of another card. Where the picture "
                  "contradicts the catalogue data of card %(letter)s, take the answers of "
                  "card %(letter)s from its catalogue data):")

# The vintage variants. The owner decided on 2026-09-24: when cards differ only by the
# vintage year, and one card states no year, that card is the card of every vintage
# that no other card states. A year counts from the name, from the slug, or from the
# label of the catalogue picture. Only the prompt of a mixed cluster, which holds cards
# that state a year and cards that state none, gets this note. So the rules of the other
# clusters stay current. Read `docs/plans/06_label-only-cluster-rules.md`.
VINTAGE_NOTE = (
    "Vintage variants. The catalogue data or the label descriptions state a vintage year "
    "for these cards: %(dated)s. They state no vintage year for these cards: "
    "%(undated)s. Check these years in the pictures. When a card that states no year and "
    "one or more cards that state a year differ only by the vintage year, rule 2a does "
    "not apply to them. Then ask a vintage question. Give each card that states a year "
    "that year. Give each card that states no year the answer \"other\": it is the card "
    "of every vintage that no other card states. When the cards differ by more than the "
    "vintage year, follow rule 2a."
)
# The answer of a card that states no year. The matcher holds the same word.
OTHER = "other"

RULES_NOTE = (
    "Label descriptions and cluster rules of the catalogue clusters. "
    "scripts/11_cluster_rules.py and the review tool write this file. The re-rank "
    "kind cluster_rules of svoe-vino-matcher reads it. Read "
    "docs/plans/05_cluster-label-rules.md."
)
NOTES_NOTE = (
    "Notes of the reviewer about the catalogue clusters. The review tool writes this "
    "file, and no script writes it. A note keeps the slugs of its cluster at the time "
    "of writing. It belongs to the current cluster that shares the most slugs with it."
)

FIELDS = ("name", "producer", "category", "grapes")
ALCOHOL = re.compile(r"-(\d{2,3})$")
# A question about a number that changes from bottle to bottle.
SERIAL = re.compile(r"serial|batch|\blot\b|bottle number|бут\.?\s*№|тираж|№")
# A question or a rule text about a feature outside the label. Some catalogue
# pictures are drawings, and a drawing shows only the label correctly. The re-rank
# sends the label crop of the query alone, so it cannot see such a feature either.
BOTTLE = re.compile(r"glass|liquid|through the|capsule|cork|neck foil|foil capsule|"
                    r"shape of the bottle|bottle shape|colou?r of the bottle|"
                    r"bottle colou?r|wine in the bottle|стекл|капсул|пробк")
ALCOHOL_WORDS = re.compile(r"alcohol|abv|% ?vol|алкогол|крепост")
PERCENT = re.compile(r"^\d{1,2}([.,]\d{1,2})?\s*%")
# A question about the vintage. `\byear\b` does not take «years», so a question
# about the years of ageing stays a `feature`.
VINTAGE_WORDS = re.compile(r"vintage|harvest|урож|\byear\b")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
# The answers that state no value. The re-rank of `svoe-vino-matcher` holds the
# same list; the two lists MUST stay equal.
NOT_VISIBLE = {"", "null", "none", "n/a", "not visible", "not shown", "unreadable",
               "unknown", "не видно"}


# ---------------------------------------------------------------- helpers

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_json(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cluster_key(slugs):
    """The key of a cluster: the SHA-1 of its sorted slugs, 12 hex digits."""
    return hashlib.sha1("\n".join(sorted(slugs)).encode("utf-8")).hexdigest()[:12]


DESCRIBE_SHA = sha256_json({"prompt": DESCRIBE_PROMPT, "model": MODEL, "thinking": THINKING,
                            "side": DESCRIBE_SIDE})[:16]
# Stage 2 sends the label crop of each card, scaled to `rules_max_side`, UP or down.
# Read `docs/plans/06_label-only-cluster-rules.md`.
RULES_PICTURE = "label crop, enlarged"
RULES_SHA = sha256_json({"prompt": RULES_PROMPT, "card": CARD_BLOCK, "model": RULES_MODEL,
                         "thinking": RULES_THINKING, "max_side": RULES_MAX_SIDE,
                         "picture": RULES_PICTURE,
                         "captions": [CAPTION, CAPTION_NO_LABEL, CAPTION_SHARED]})[:16]


def normalize(text):
    """The compared form of an answer, or None for an answer that states no value.

    Lower case, `ё` as `е`, no quotes or end punctuation, no space around `/`, `-`,
    `:` and `%`. `30 / 70` gives `30/70`.
    """
    if text is None:
        return None
    t = str(text).strip().lower().replace("ё", "е")
    t = t.strip(" \t\n\"'«»`.,;:!?()[]")
    t = re.sub(r"\s*([/\-:%])\s*", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    return None if t in NOT_VISIBLE else t


def alcohol_of(slug):
    """The alcohol value that the slug states, as text, or None. `-145` is 14.5 %."""
    m = ALCOHOL.search(slug or "")
    if not m:
        return None
    digits = m.group(1)
    return (digits if len(digits) == 2 else digits[:2] + "." + digits[2:]) + " %"


def card_data(slug, catalog):
    rec = catalog.get(slug) or {}
    out = {f: (rec.get(f) or "").strip() for f in FIELDS}
    out["alcohol"] = alcohol_of(slug)
    return out


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def write_json(path, obj):
    """Write `obj` to `path` atomically."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = "%s.tmp.%d.%d" % (path, os.getpid(), threading.get_ident())
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, path)


@contextlib.contextmanager
def locked(path):
    """Hold the lock file of `path`. The CLI and the review tool use the same lock."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".lock", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def load_catalog():
    out = {}
    with open(common.CATALOG_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["slug"]] = rec
    return out


def load_clusters():
    """The clusters of `scripts/10_clusters.py`, or an empty list."""
    return (load_json(common.CLUSTERS_FILE, {}) or {}).get("clusters") or []


def picture_resolver(catalog):
    """slug -> the catalogue picture of the review tool, or None."""
    crops = common.load_cropped_bottles()
    patches = common.load_patches()
    return lambda slug: common.catalogue_picture(slug, catalog.get(slug), crops, patches)


_LABELS = None


def label_pictures():
    """slug -> the label crop of `bottle_label_dir`, the picture of stage 2.

    The crop holds the label alone, and its alpha channel is the label mask. On white
    it is the view that the re-rank sends for a query. The map is read once for each
    process. An unset `bottle_label_dir` gives an empty map.
    """
    global _LABELS
    if _LABELS is None:
        _LABELS = common.load_bottle_labels(common.BOTTLE_LABEL_DIR)
    return _LABELS


def encode_picture(path, max_side, enlarge=False):
    """A PNG data URL of the picture on white, with the long side at most `max_side`.

    `enlarge` also scales a smaller picture UP to that long side. The gateway refuses
    a WebP data URL with HTTP 400, so every picture goes as PNG.
    """
    from PIL import Image
    with Image.open(path) as src:
        src.load()
        if src.mode in ("RGBA", "LA", "P"):
            rgba = src.convert("RGBA")
            im = Image.new("RGB", rgba.size, (255, 255, 255))
            im.paste(rgba, mask=rgba.split()[-1])
        else:
            im = src.convert("RGB")
    if max(im.size) > max_side or enlarge and max(im.size) < max_side:
        s = max_side / max(im.size)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                       Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"), im.size


def image_tokens(size):
    """An estimate of the tokens of one picture: one token for each 32 x 32 pixels."""
    return math.ceil(size[0] / 32) * math.ceil(size[1] / 32) + 4


def parse_json(text):
    """The JSON object of an answer, or None."""
    try:
        value = json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text or "", re.S)
        if not m:
            return None
        try:
            value = json.loads(m.group(0))
        except ValueError:
            return None
    return value if isinstance(value, dict) else None


# ---------------------------------------------------------------- the VLM

class VlmError(RuntimeError):
    pass


class Vlm:
    """One OpenAI-compatible chat route, with JSON answers and temperature 0.

    `api` is `llama.cpp` (the gx10 gateway: `chat_template_kwargs.enable_thinking`,
    no key) or `qwencloud` (a top field `enable_thinking`, the key from the variable
    `key_env`). A JSON mode is not sent with thinking; `parse_json` reads the answer.
    """

    def __init__(self, url=URL, model=MODEL, thinking=THINKING, timeout_s=TIMEOUT_S,
                 retries=3, api="llama.cpp", key_env=""):
        self.url, self.model, self.thinking = url, model, thinking
        self.timeout_s, self.retries = timeout_s, retries
        self.api, self.key_env = api, key_env
        # The second attempt for an answer that reached `max_tokens`.
        self.loop_guard = LOOP_GUARD if api == "llama.cpp" else {"max_tokens": 32000}
        self.calls = self.failed = self.hits = 0
        self.total_ms = 0.0

    @staticmethod
    def _result(answer, ms):
        choice = (answer.get("choices") or [{}])[0]
        return {"text": ((choice.get("message") or {}).get("content") or "").strip(),
                "ms": round(ms), "usage": answer.get("usage") or {},
                "finish_reason": choice.get("finish_reason")}

    def ask(self, content, max_tokens, extra=None):
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}],
        }
        # The QwenCloud route takes JSON mode with thinking (measured on 2026-09-24); one
        # rule of `qwen3.8-max` without it held a broken string. The local gateway runs
        # with thinking off and takes JSON mode as a grammar.
        if not self.thinking or self.api == "qwencloud":
            payload["response_format"] = {"type": "json_object"}
        if self.api == "qwencloud":
            payload["enable_thinking"] = self.thinking
        else:
            payload["chat_template_kwargs"] = {"enable_thinking": self.thinking}
        payload.update(extra or {})
        # A repeated request reads the answer of `model_cache`, and needs no key. `hits`
        # counts these answers; `calls` and `total_ms` count the requests alone.
        fields = model_cache.vlm_fields(self.url, payload)
        record = model_cache.lookup(fields) if fields else None
        if record is not None:
            self.hits += 1
            return self._result(record["answer"], record["ms"])
        headers = {"Content-Type": "application/json"}
        if self.key_env:
            key = os.environ.get(self.key_env)
            if not key:
                self.failed += 1
                raise VlmError("the environment variable %s is not set" % self.key_env)
            headers["Authorization"] = "Bearer " + key
        body = json.dumps(payload).encode("utf-8")
        delay, last = 5.0, None
        for _ in range(self.retries):
            t0 = time.perf_counter()
            try:
                req = urllib.request.Request(self.url, data=body, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    answer = json.load(resp)
            except urllib.error.HTTPError as exc:
                last = "http %d: %s" % (exc.code, exc.read()[:300].decode("utf-8", "replace"))
                if exc.code == 429 or exc.code >= 500:
                    time.sleep(delay)
                    delay *= 2
                    continue
                break           # another 4xx does not change on a second attempt
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                last = repr(exc)
                time.sleep(delay)
                delay *= 2
                continue
            ms = (time.perf_counter() - t0) * 1000
            self.calls += 1
            self.total_ms += ms
            if fields and answer.get("choices"):
                model_cache.store(fields, answer, ms)
            return self._result(answer, ms)
        self.failed += 1
        raise VlmError(last or "no answer")


# ---------------------------------------------------------------- stage 1

def picture_stat(path):
    st = os.stat(path)
    return [int(st.st_mtime), st.st_size]


def description_current(rec, path):
    """True when the description of `rec` belongs to the picture of `path`."""
    if not rec or rec.get("error") or not path:
        return False
    if rec.get("settings_sha") != DESCRIBE_SHA or rec.get("picture") != path:
        return False
    try:
        return rec.get("picture_stat") == picture_stat(path)
    except OSError:
        return False


def looped(rec):
    """True when the answer of `rec` reached `max_tokens`."""
    return "finish_reason length" in ((rec or {}).get("error") or "")


def describe(vlm, path, guard=False):
    """Stage 1 for one card. Answer the description record.

    `guard` sends the request with `LOOP_GUARD`.
    """
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    url, size = encode_picture(path, DESCRIBE_SIDE, enlarge=True)
    rec = {"picture": path, "picture_sha256": digest, "picture_stat": picture_stat(path),
           "sent_size": list(size), "settings_sha": DESCRIBE_SHA, "built_at": now(),
           "description": None, "error": None}
    if guard:
        rec["loop_guard"] = vlm.loop_guard
    try:
        out = vlm.ask([{"type": "image_url", "image_url": {"url": url}},
                       {"type": "text", "text": DESCRIBE_PROMPT}], DESCRIBE_MAX_TOKENS,
                      extra=vlm.loop_guard if guard else None)
    except VlmError as exc:
        rec["error"] = str(exc)
        return rec
    rec["ms"], rec["usage"] = out["ms"], out["usage"]
    value = parse_json(out["text"])
    if value is None:
        rec["error"] = "the answer is not a JSON object (finish_reason %s)" % out["finish_reason"]
        rec["raw"] = out["text"][:4000]
    else:
        rec["description"] = value
    return rec


# ---------------------------------------------------------------- stage 2

def vintage_facts(slugs, catalog, cards):
    """The vintage years that each card states, and the cards that state no year.

    A card states a year in its name, in its slug, or on its label: the key `vintage`
    of its label description. A year of the name or the slug wins over the year of the
    label. A card states no year when its name and its slug hold no year and its
    description gives no vintage. A card with an unreadable or an implausible label
    year, or with no description, is in neither group.

    Answer `(dated, undated)`. `dated` maps a slug to `{"years", "where"}`. `undated`
    lists the slugs in the order of `slugs`.
    """
    last = int(time.strftime("%Y"))
    dated, undated = {}, []
    for s in slugs:
        name = ((catalog or {}).get(s) or {}).get("name") or ""
        named = set(YEAR.findall(name)) | set(YEAR.findall(s))
        desc = ((cards or {}).get(s) or {}).get("description")
        label, state = None, "unknown"
        if isinstance(desc, dict):
            value = desc.get("vintage")
            text = "" if value is None else str(value).strip().lower()
            if text in ("", "null", "none", "n/a"):
                state = "none"
            else:
                found = {y for y in YEAR.findall(text) if 1900 <= int(y) <= last}
                if len(found) == 1:
                    state, label = "year", found.pop()
        if named:
            dated[s] = {"years": named, "where": "in the name"}
        elif label:
            dated[s] = {"years": {label}, "where": "on the label"}
        elif state == "none":
            undated.append(s)
    return dated, undated


def vintage_note(letters, catalog, cards):
    """The note of `VINTAGE_NOTE` for a mixed cluster, or an empty text."""
    dated, undated = vintage_facts(list(letters.values()), catalog, cards)
    if not dated or not undated:
        return ""
    letter = {s: x for x, s in letters.items()}
    return VINTAGE_NOTE % {
        "dated": "; ".join("Card %s: %s, %s" % (letter[s], ", ".join(sorted(f["years"])),
                                                 f["where"])
                           for s, f in sorted(dated.items(), key=lambda kv: letter[kv[0]])),
        "undated": ", ".join("Card %s" % letter[s] for s in undated)}


def rule_inputs_sha(slugs, catalog, cards, note_text):
    """The SHA-256 of every input of stage 2. A different value makes a rule stale.

    `label_pictures` holds the path of each label crop. The path, and not the bytes,
    enters the SHA, so that the page `/clusters` reads no picture for the status. A
    crop that is cut again under the same path does not make a rule stale.

    The note of the vintage variants enters the SHA only when a cluster has one, so
    the rule of a cluster without the note keeps its SHA.
    """
    slugs = sorted(slugs)
    labels = label_pictures()
    inputs = {
        "slugs": slugs,
        "cards": {s: card_data(s, catalog) for s in slugs},
        "pictures": {s: (cards.get(s) or {}).get("picture_sha256") for s in slugs},
        "labels": {s: labels.get(s) for s in slugs},
        "descriptions": {s: sha256_json((cards.get(s) or {}).get("description")) for s in slugs},
        "note": note_text or "",
        "settings": RULES_SHA,
    }
    vintage = vintage_note({LETTERS[i]: s for i, s in enumerate(slugs)}, catalog, cards)
    if vintage:
        inputs["vintage_note"] = vintage
    return sha256_json(inputs)[:16]


def rules_content(letters, catalog, cards, note_text, picture_of, max_side):
    """The message content of stage 2, and an estimate of its tokens.

    Each card goes with its label crop, scaled to `max_side`, UP or down. A card
    with no label crop goes with the picture of `picture_of`, and its caption states
    that. The caption of a card also names the cards with the same catalogue picture.
    The key `bottle` of the label description stays out: the bottle and the capsule
    are not on the label, and a drawing can show them wrong.
    """
    labels = label_pictures()
    shas = {s: (cards.get(s) or {}).get("picture_sha256") for s in letters.values()}
    content, tokens, blocks = [], 0, []
    for letter, slug in letters.items():
        twins = [x for x, s in letters.items()
                 if s != slug and shas[slug] and shas[s] == shas[slug]]
        path = labels.get(slug)
        if not path:
            path = picture_of(slug)
            caption = CAPTION_NO_LABEL % {"letter": letter}
        elif twins:
            caption = CAPTION_SHARED % {"letter": letter, "twins": ", ".join(twins)}
        else:
            caption = CAPTION % {"letter": letter}
        content.append({"type": "text", "text": caption})
        if path:
            url, size = encode_picture(path, max_side, enlarge=True)
            content.append({"type": "image_url", "image_url": {"url": url}})
            tokens += image_tokens(size)
        else:
            content.append({"type": "text", "text": "(no catalogue photo)"})
        data = card_data(slug, catalog)
        desc = (cards.get(slug) or {}).get("description")
        if isinstance(desc, dict):
            desc = {k: v for k, v in desc.items() if k != "bottle"}
        blocks.append(CARD_BLOCK % {
            "letter": letter, "name": data["name"], "producer": data["producer"],
            "category": data["category"], "grapes": data["grapes"],
            "alcohol": ('"%s"' % data["alcohol"]) if data["alcohol"] else "unknown",
            "description": json.dumps(desc, ensure_ascii=False) if desc else "none",
        })
    text = RULES_PROMPT % {"n": len(letters), "last": list(letters)[-1],
                           "cards": "\n\n".join(blocks),
                           "notes": (note_text or "").strip() or "none"}
    vintage = vintage_note(letters, catalog, cards)
    if vintage:
        head = "\n\nAnswer with one JSON object:"
        text = text.replace(head, "\n\n" + vintage + head, 1)
    content.append({"type": "text", "text": text})
    return content, tokens + int(len(text) / 2.5)


def clean_answer(value):
    """The text of one expected answer, or None when it states no value."""
    if value is None or isinstance(value, bool) and not value:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = text.strip()
    return text if normalize(text) is not None else None


def question_kind(text, answers):
    """`serial`, `bottle`, `alcohol`, `vintage`, or `feature`, for the rules the code
    enforces."""
    t = (text or "").lower()
    if SERIAL.search(t):
        return "serial"
    if BOTTLE.search(t):
        return "bottle"
    values = [a for a in answers.values() if a is not None]
    if ALCOHOL_WORDS.search(t) or values and all(PERCENT.match(a.strip()) for a in values):
        return "alcohol"
    if VINTAGE_WORDS.search(t) or values and all(YEAR.fullmatch(a.strip()) for a in values):
        return "vintage"
    return "feature"


def named_year(answer, slug, catalog):
    """The expected answer of a vintage question when the card data states it, or None.

    The answer stays when it holds a year and the name or the slug of the card holds
    every year of the answer.
    """
    if answer is None:
        return None
    years = YEAR.findall(answer)
    name = ((catalog or {}).get(slug) or {}).get("name") or ""
    return answer if years and all(y in name or y in slug for y in years) else None


def vintage_answer(answer, slug, dated, catch_all):
    """The expected answer of a vintage question in a rule with vintage variants.

    A card that states a year keeps a single year of `dated`, as the bare year. A card
    of `catch_all` keeps `other`. Every other answer is None.
    """
    if answer is None:
        return None
    if slug in catch_all:
        return OTHER if normalize(answer) == OTHER else None
    years = set(YEAR.findall(answer))
    if slug in dated and len(years) == 1 and years <= dated[slug]["years"]:
        return years.pop()
    return None


def check_rule(value, letters, catalog=None, cards=None):
    """Check the answer of stage 2 and set the mode. The letters become slugs.

    The code enforces five rules of the prompt, because the model did not always keep
    them:

    - A question about a bottle number is never valid: the number changes from bottle
      to bottle.
    - A question about a feature outside the label is never valid, and a rule text
      about such a feature gives mode `none`, not `verdict`. Some catalogue pictures
      are drawings, and a drawing shows only the label correctly.
    - A vintage question keeps the expected year of a card only when the name or the
      slug of the card states that year. A year that only the picture shows changes
      from bottle to bottle.
    - The vintage variants of `VINTAGE_NOTE`. The model marks a card that states no
      year with `other`. The mark stays only when the card states no year, and when
      another question of the rule separates it from no card that states a year: the
      two cards differ only by the vintage. Then a vintage question also keeps the year
      on the label of a card. Else the rule above applies. `cards` holds the label
      descriptions.
    - A question about the alcohol value is valid only when no other question is
      valid.
    """
    questions = []
    for q in value.get("questions") or []:
        if not isinstance(q, dict):
            continue
        text = str(q.get("question") or "").strip()
        given = q.get("answers") if isinstance(q.get("answers"), dict) else {}
        answers = {}
        for letter, slug in letters.items():
            answers[slug] = clean_answer(given.get(letter, given.get(slug)))
        questions.append({"id": "q%d" % (len(questions) + 1), "question": text,
                          "answers": answers, "kind": question_kind(text, answers)})

    # The vintage variants: the cards that state no year, and that differ from a card
    # with a year only by the vintage in every other question.
    dated, undated = vintage_facts(list(letters.values()), catalog, cards)

    def only_vintage_differs(a, b):
        for q in questions:
            if q["kind"] in ("vintage", "serial", "bottle", "alcohol"):
                continue
            x, y = normalize(q["answers"].get(a)), normalize(q["answers"].get(b))
            if x is not None and y is not None and x != y:
                return False
        return True

    variants = {u for u in undated if any(only_vintage_differs(u, d) for d in dated)}
    catch_all = {u for u in variants
                 if any(q["kind"] == "vintage" and normalize(q["answers"].get(u)) == OTHER
                        for q in questions)}

    for q in questions:
        if q["kind"] == "vintage":
            q["answers"] = {s: (vintage_answer(a, s, dated, catch_all) if catch_all
                                else named_year(a, s, catalog))
                            for s, a in q["answers"].items()}
        distinct = {normalize(a) for a in q["answers"].values() if a is not None}
        q["valid"] = (bool(q["question"]) and len(distinct) >= 2
                      and q["kind"] not in ("serial", "bottle"))
    if any(q["valid"] and q["kind"] in ("feature", "vintage") for q in questions):
        for q in questions:
            if q["kind"] == "alcohol":
                q["valid"] = False
    groups = []
    for g in value.get("indistinguishable") or []:
        if isinstance(g, list):
            members = sorted({letters[x] for x in g if isinstance(x, str) and x in letters})
            if len(members) >= 2:
                groups.append(members)
    rule = str(value.get("rule") or "").strip()
    if any(q["valid"] for q in questions):
        mode = "sheet"
    elif rule and not BOTTLE.search(rule.lower()):
        mode = "verdict"
    else:
        mode = "none"
    return {"mode": mode, "differences": str(value.get("differences") or "").strip(),
            "questions": questions, "rule": rule, "indistinguishable": groups}


def build_rule(vlm, slugs, catalog, cards, note_text, picture_of, guard=False):
    """Stage 2 for one cluster. Answer the cluster rule record.

    `guard` sends the request with `LOOP_GUARD`.
    """
    slugs = sorted(slugs)
    if len(slugs) > len(LETTERS):
        raise ValueError("a cluster of %d cards has no letters" % len(slugs))
    letters = {LETTERS[i]: s for i, s in enumerate(slugs)}
    rec = {"key": cluster_key(slugs), "slugs": slugs, "letters": letters,
           "inputs_sha": rule_inputs_sha(slugs, catalog, cards, note_text),
           "note": note_text or "", "built_at": now(), "mode": "none", "error": None}
    side = RULES_MAX_SIDE
    while True:
        content, estimate = rules_content(letters, catalog, cards, note_text, picture_of, side)
        if estimate <= TOKEN_BUDGET or side <= 256:
            break
        side = int(side * 0.75)
    rec["max_side"], rec["prompt_tokens_estimate"] = side, estimate
    if guard:
        rec["loop_guard"] = vlm.loop_guard
    rec["model"] = vlm.model
    try:
        out = vlm.ask(content, RULES_MAX_TOKENS, extra=vlm.loop_guard if guard else None)
    except VlmError as exc:
        rec["error"] = str(exc)
        return rec
    rec["ms"], rec["usage"] = out["ms"], out["usage"]
    value = parse_json(out["text"])
    if value is None:
        rec["error"] = "the answer is not a JSON object (finish_reason %s)" % out["finish_reason"]
        rec["raw"] = out["text"][:4000]
        return rec
    rec.update(check_rule(value, letters, catalog, cards))
    rec["answer"] = value
    return rec


def rule_status(rec, inputs_sha):
    """`none`, `error`, `stale`, or `current`."""
    if not rec:
        return "none"
    if rec.get("error"):
        return "error"
    return "current" if rec.get("inputs_sha") == inputs_sha else "stale"


# ---------------------------------------------------------------- the files

def load_rules():
    data = load_json(RULES_FILE, {}) or {}
    data.setdefault("version", 1)
    data["note"] = RULES_NOTE
    data.setdefault("cards", {})
    data.setdefault("clusters", {})
    return data


def update_rules(change):
    """Read the rules file, apply `change`, and write the file, under the lock."""
    with locked(RULES_FILE):
        data = load_rules()
        change(data)
        data["settings"] = {"url": URL, "model": MODEL, "thinking": THINKING,
                            "rules_url": RULES_URL, "rules_model": RULES_MODEL,
                            "rules_thinking": RULES_THINKING,
                            "describe_side": DESCRIBE_SIDE,
                            "rules_max_side": RULES_MAX_SIDE,
                            "describe_sha": DESCRIBE_SHA, "rules_sha": RULES_SHA}
        data["prompts"] = {"describe": DESCRIBE_PROMPT, "rules": RULES_PROMPT,
                           "card": CARD_BLOCK}
        data["updated_at"] = now()
        write_json(RULES_FILE, data)
    return data


def edit_rule(slugs, value, catalog):
    """Replace the reviewer-editable parts of one stored cluster rule.

    `value` holds the rule text and at most three difference-sheet questions. Each
    question maps the current slugs to its expected answers. The same checks as a VLM
    build set the question kinds, valid flags, and mode. Build metadata and the input
    SHA stay unchanged, so a manual edit stays current until a rule input changes.
    """
    if not isinstance(slugs, list) or not slugs or not all(isinstance(s, str) for s in slugs):
        raise ValueError("slugs MUST be a non-empty list of slugs")
    if not isinstance(value, dict):
        raise ValueError("rule MUST be an object")
    rule_text = value.get("rule")
    if not isinstance(rule_text, str):
        raise ValueError("rule text MUST be a string")
    rule_text = rule_text.strip()
    if len(rule_text) > 4000:
        raise ValueError("rule text is longer than 4000 characters")
    questions = value.get("questions")
    if not isinstance(questions, list):
        raise ValueError("questions MUST be a list")
    if len(questions) > 3:
        raise ValueError("a rule can have at most 3 questions")

    members = set(slugs)
    clean_questions = []
    for i, question in enumerate(questions, 1):
        if not isinstance(question, dict):
            raise ValueError("question %d MUST be an object" % i)
        text = question.get("question")
        answers = question.get("answers")
        if not isinstance(text, str):
            raise ValueError("question %d text MUST be a string" % i)
        text = text.strip()
        if len(text) > 500:
            raise ValueError("question %d is longer than 500 characters" % i)
        if not isinstance(answers, dict):
            raise ValueError("question %d answers MUST be an object" % i)
        extra = set(answers) - members
        if extra:
            raise ValueError("question %d has an answer for a card outside the cluster" % i)
        clean_answers = {}
        for slug in slugs:
            answer = answers.get(slug)
            if answer is not None and not isinstance(answer, str):
                raise ValueError("question %d answers MUST be strings or null" % i)
            answer = answer.strip() if isinstance(answer, str) else None
            if answer and len(answer) > 500:
                raise ValueError("question %d has an answer longer than 500 characters" % i)
            clean_answers[slug] = answer or None
        if text or any(clean_answers.values()):
            clean_questions.append({"question": text, "answers": clean_answers})

    key = cluster_key(slugs)
    edited = None

    def change(data):
        nonlocal edited
        old = data["clusters"].get(key)
        if not old or sorted(old.get("slugs") or []) != sorted(slugs):
            raise ValueError("this cluster has no stored rule; load the page again")
        letters = old.get("letters") or {}
        if set(letters.values()) != members:
            raise ValueError("the stored rule has a different set of cards; load the page again")
        by_slug = {slug: letter for letter, slug in letters.items()}
        raw = {
            "differences": old.get("differences") or "",
            "questions": [{
                "question": q["question"],
                "answers": {by_slug[slug]: q["answers"][slug] for slug in slugs},
            } for q in clean_questions],
            "rule": rule_text,
            "indistinguishable": [[by_slug[slug] for slug in group if slug in by_slug]
                                    for group in old.get("indistinguishable") or []],
        }
        checked = check_rule(raw, letters, catalog, data.get("cards") or {})
        stamp = now()
        edited = {**old, **checked, "answer": raw, "edited_at": stamp}
        if "generated_answer" not in edited and old.get("answer") is not None:
            edited["generated_answer"] = old["answer"]
        data["clusters"][key] = edited

    update_rules(change)
    return edited


def load_notes():
    data = load_json(NOTES_FILE, {}) or {}
    return [n for n in data.get("notes") or []
            if isinstance(n, dict) and n.get("slugs") and (n.get("text") or "").strip()]


def assign_notes(clusters, notes):
    """cluster key -> the notes of that cluster.

    A note goes to the current cluster that shares the most slugs with it. A tie goes
    to the cluster that comes first in the file.
    """
    where = {}
    for c in clusters:
        key = cluster_key(c["slugs"])
        for s in c["slugs"]:
            where[s] = key
    out = collections.defaultdict(list)
    for n in notes:
        counts = collections.Counter(where[s] for s in n["slugs"] if s in where)
        if counts:
            out[counts.most_common(1)[0][0]].append(n)
    return out


def note_text(notes):
    return "\n".join(n["text"].strip() for n in notes)


def set_note(slugs, text, clusters):
    """Store `text` as the note of the cluster of `slugs`. An empty text clears it.

    Every note of that cluster is replaced, so the cluster keeps one note with its
    current slugs. Answer the new note, or None.
    """
    slugs = sorted(slugs)
    text = (text or "").strip()
    with locked(NOTES_FILE):
        data = load_json(NOTES_FILE, {}) or {}
        notes = [n for n in data.get("notes") or [] if isinstance(n, dict)]
        valid = [n for n in notes if n.get("slugs") and (n.get("text") or "").strip()]
        drop = {id(n) for n in assign_notes(clusters, valid).get(cluster_key(slugs), [])}
        keep = [n for n in notes if id(n) not in drop]
        new = None
        if text:
            new = {"slugs": slugs, "text": text, "updated_at": now()}
            keep.append(new)
        write_json(NOTES_FILE, {"version": 1, "note": NOTES_NOTE, "notes": keep})
    return new


# ---------------------------------------------------------------- one cluster

class Builder:
    """Run the two stages for the cards and the clusters that are not current."""

    def __init__(self, catalog, picture_of, vlm=None, log=common.log, rules_vlm=None):
        self.catalog = catalog
        self.picture_of = picture_of
        self.vlm = vlm or Vlm()
        self.rules_vlm = rules_vlm or Vlm(
            url=RULES_URL, model=RULES_MODEL, thinking=RULES_THINKING,
            timeout_s=RULES_TIMEOUT_S, api=RULES_API, key_env=RULES_KEY_ENV)
        self.log = log

    def describe_cards(self, slugs, force=False):
        """Stage 1 for each card of `slugs` whose description is not current.

        Answer the number of calls.
        """
        calls = 0
        cards = load_rules()["cards"]
        for slug in slugs:
            path = self.picture_of(slug)
            if not path:
                if (cards.get(slug) or {}).get("error") != "no catalogue picture":
                    rec = {"picture": None, "description": None, "built_at": now(),
                           "error": "no catalogue picture"}
                    update_rules(lambda d, s=slug, r=rec: d["cards"].__setitem__(s, r))
                continue
            if not force and description_current(cards.get(slug), path):
                continue
            # An answer that looped once loops again: go to the guard at once.
            guard = looped(cards.get(slug))
            rec = describe(self.vlm, path, guard=guard)
            calls += 1
            if looped(rec) and not guard:
                self.log("describe %s: the answer reached max_tokens; again with %s"
                         % (slug, LOOP_GUARD))
                rec = describe(self.vlm, path, guard=True)
                calls += 1
            update_rules(lambda d, s=slug, r=rec: d["cards"].__setitem__(s, r))
            self.log("describe %s: %s ms%s" % (slug, rec.get("ms", "-"),
                                               "  ERROR " + rec["error"] if rec["error"] else ""))
        return calls

    def build(self, slugs, notes, force=False):
        """Stage 2 for one cluster when its rule is not current.

        Answer the rule record and whether a call was made.
        """
        data = load_rules()
        text = note_text(notes)
        key = cluster_key(slugs)
        old = data["clusters"].get(key)
        sha = rule_inputs_sha(slugs, self.catalog, data["cards"], text)
        if not force and rule_status(old, sha) == "current":
            return old, False
        guard = looped(old)
        rec = build_rule(self.rules_vlm, slugs, self.catalog, data["cards"], text,
                         self.picture_of, guard=guard)
        if looped(rec) and not guard:
            self.log("rule %s: the answer reached max_tokens; again with %s"
                     % (key, self.rules_vlm.loop_guard))
            rec = build_rule(self.rules_vlm, slugs, self.catalog, data["cards"], text,
                             self.picture_of, guard=True)
        update_rules(lambda d: d["clusters"].__setitem__(key, rec))
        self.log("rule %s (%d cards): mode %s, %d valid questions, %s ms%s"
                 % (key, len(slugs), rec["mode"],
                    sum(1 for q in rec.get("questions") or [] if q["valid"]),
                    rec.get("ms", "-"), "  ERROR " + rec["error"] if rec["error"] else ""))
        return rec, True
