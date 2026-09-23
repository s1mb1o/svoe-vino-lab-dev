"""The label rules of the catalogue clusters.

Read `docs/plans/05_cluster-label-rules.md`. The terms of that plan are the terms
of this module.

Stage 1 asks the VLM to describe the label of one card. The call sends the
catalogue picture and no card data, so the description holds what the model sees.

Stage 2 asks the VLM where the labels of one cluster differ. The call sends the
pictures of all cards of the cluster, the card data, the label descriptions, and the
note of the reviewer. The answer is a difference sheet, which holds questions with the
expected answer of each card, and a rule text. The code checks the sheet and sets
the mode of the cluster rule:

    sheet    at least one question separates two cards
    verdict  no question separates two cards, and the rule text is not empty
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
import threading
import time
import urllib.error
import urllib.request

import common

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

DESCRIBE_MAX_TOKENS = 1500
RULES_MAX_TOKENS = 2500
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
    "You see the catalogue photos of %(n)d wine cards, Card A to Card %(last)s. "
    "A recognizer confuses these cards, because their bottles look alike.\n\n"
    "The catalogue data and the label description of each card:\n\n%(cards)s\n\n"
    "Notes of the reviewer about these cards:\n%(notes)s\n\n"
    "Task: find the features of the bottle label that tell the cards apart. Later, a "
    "model will look at a customer photo of ONE of these bottles and answer your "
    "questions. The answers MUST identify the card.\n\n"
    "Rules:\n"
    "1. Write 1 to 3 short questions about the label. A person MUST be able to answer "
    "each question by looking at the bottle.\n"
    "2. For each question, give the expected answer of each card as a short text, such "
    "as \"2019\", \"30/70\" or \"gold\". Give null when the label of the card does not "
    "show this feature.\n"
    "3. Use a question only when at least two cards have different answers.\n"
    "4. The notes of the reviewer are correct. Use them first.\n"
    "5. Compare first the wine name and the grape names that each label prints. A "
    "different name is the strongest feature.\n"
    "6. Do not use a bottle number, a batch number, a lot number or a serial number, "
    "such as «Бут. №» or «Тираж». These numbers change from bottle to bottle.\n"
    "7. The catalogue data is correct. A catalogue photo can be too small to show a "
    "small text. Then take the value from the catalogue data, for example a year or a "
    "ratio in the name.\n"
    "8. A model wrote the label descriptions, and they can hold errors. Use a feature "
    "only when you see it in the photos, or when the catalogue data or the notes of the "
    "reviewer state it.\n"
    "9. Two texts that differ only by their alphabet, such as ФАНТОМ and PHANTOM, are "
    "the same text and are not a difference.\n"
    "10. The alcohol value can change between two vintages of one wine. Use it only "
    "when no other feature differs.\n"
    "11. List the groups of cards that no feature tells apart in \"indistinguishable\".\n"
    "12. Also write the rule as one short plain text, for example: \"If the label shows "
    "2024, it is card A; otherwise it is card B.\"\n\n"
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
ALCOHOL_WORDS = re.compile(r"alcohol|abv|% ?vol|алкогол|крепост")
PERCENT = re.compile(r"^\d{1,2}([.,]\d{1,2})?\s*%")
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
RULES_SHA = sha256_json({"prompt": RULES_PROMPT, "card": CARD_BLOCK, "model": MODEL,
                         "thinking": THINKING, "max_side": RULES_MAX_SIDE})[:16]


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
    """The chat route of the gateway, with JSON answers, thinking off, temperature 0."""

    def __init__(self, url=URL, model=MODEL, thinking=THINKING, timeout_s=TIMEOUT_S,
                 retries=3):
        self.url, self.model, self.thinking = url, model, thinking
        self.timeout_s, self.retries = timeout_s, retries
        self.calls = self.failed = 0
        self.total_ms = 0.0

    def ask(self, content, max_tokens, extra=None):
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": self.thinking},
            "messages": [{"role": "user", "content": content}],
        }
        payload.update(extra or {})
        body = json.dumps(payload).encode("utf-8")
        delay, last = 5.0, None
        for _ in range(self.retries):
            t0 = time.perf_counter()
            try:
                req = urllib.request.Request(self.url, data=body,
                                             headers={"Content-Type": "application/json"})
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
            choice = (answer.get("choices") or [{}])[0]
            return {"text": ((choice.get("message") or {}).get("content") or "").strip(),
                    "ms": round(ms), "usage": answer.get("usage") or {},
                    "finish_reason": choice.get("finish_reason")}
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
        rec["loop_guard"] = LOOP_GUARD
    try:
        out = vlm.ask([{"type": "image_url", "image_url": {"url": url}},
                       {"type": "text", "text": DESCRIBE_PROMPT}], DESCRIBE_MAX_TOKENS,
                      extra=LOOP_GUARD if guard else None)
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

def rule_inputs_sha(slugs, catalog, cards, note_text):
    """The SHA-256 of every input of stage 2. A different value makes a rule stale."""
    slugs = sorted(slugs)
    return sha256_json({
        "slugs": slugs,
        "cards": {s: card_data(s, catalog) for s in slugs},
        "pictures": {s: (cards.get(s) or {}).get("picture_sha256") for s in slugs},
        "descriptions": {s: sha256_json((cards.get(s) or {}).get("description")) for s in slugs},
        "note": note_text or "",
        "settings": RULES_SHA,
    })[:16]


def rules_content(letters, catalog, cards, note_text, picture_of, max_side):
    """The message content of stage 2, and an estimate of its tokens."""
    content, tokens, blocks = [], 0, []
    for letter, slug in letters.items():
        content.append({"type": "text", "text": "Card %s:" % letter})
        path = picture_of(slug)
        if path:
            url, size = encode_picture(path, max_side)
            content.append({"type": "image_url", "image_url": {"url": url}})
            tokens += image_tokens(size)
        else:
            content.append({"type": "text", "text": "(no catalogue photo)"})
        data = card_data(slug, catalog)
        desc = (cards.get(slug) or {}).get("description")
        blocks.append(CARD_BLOCK % {
            "letter": letter, "name": data["name"], "producer": data["producer"],
            "category": data["category"], "grapes": data["grapes"],
            "alcohol": ('"%s"' % data["alcohol"]) if data["alcohol"] else "unknown",
            "description": json.dumps(desc, ensure_ascii=False) if desc else "none",
        })
    text = RULES_PROMPT % {"n": len(letters), "last": list(letters)[-1],
                           "cards": "\n\n".join(blocks),
                           "notes": (note_text or "").strip() or "none"}
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
    """`serial`, `alcohol`, or `feature`, for the two rules the code enforces."""
    t = (text or "").lower()
    if SERIAL.search(t):
        return "serial"
    values = [a for a in answers.values() if a is not None]
    if ALCOHOL_WORDS.search(t) or values and all(PERCENT.match(a.strip()) for a in values):
        return "alcohol"
    return "feature"


def check_rule(value, letters):
    """Check the answer of stage 2 and set the mode. The letters become slugs.

    The code enforces two rules of the prompt, because the model did not always keep
    them in the first probe. A question about a bottle number is never valid: the
    number changes from bottle to bottle. A question about the alcohol value is valid
    only when no other question is valid.
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
        distinct = {normalize(a) for a in answers.values() if a is not None}
        kind = question_kind(text, answers)
        valid = bool(text) and len(distinct) >= 2 and kind != "serial"
        questions.append({"id": "q%d" % (len(questions) + 1), "question": text,
                          "answers": answers, "kind": kind, "valid": valid})
    if any(q["valid"] and q["kind"] == "feature" for q in questions):
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
    elif rule:
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
        rec["loop_guard"] = LOOP_GUARD
    try:
        out = vlm.ask(content, RULES_MAX_TOKENS, extra=LOOP_GUARD if guard else None)
    except VlmError as exc:
        rec["error"] = str(exc)
        return rec
    rec["ms"], rec["usage"] = out["ms"], out["usage"]
    value = parse_json(out["text"])
    if value is None:
        rec["error"] = "the answer is not a JSON object (finish_reason %s)" % out["finish_reason"]
        rec["raw"] = out["text"][:4000]
        return rec
    rec.update(check_rule(value, letters))
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
                            "describe_side": DESCRIBE_SIDE,
                            "rules_max_side": RULES_MAX_SIDE,
                            "describe_sha": DESCRIBE_SHA, "rules_sha": RULES_SHA}
        data["prompts"] = {"describe": DESCRIBE_PROMPT, "rules": RULES_PROMPT,
                           "card": CARD_BLOCK}
        data["updated_at"] = now()
        write_json(RULES_FILE, data)
    return data


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

    def __init__(self, catalog, picture_of, vlm=None, log=common.log):
        self.catalog = catalog
        self.picture_of = picture_of
        self.vlm = vlm or Vlm()
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
        rec = build_rule(self.vlm, slugs, self.catalog, data["cards"], text, self.picture_of,
                         guard=guard)
        if looped(rec) and not guard:
            self.log("rule %s: the answer reached max_tokens; again with %s" % (key, LOOP_GUARD))
            rec = build_rule(self.vlm, slugs, self.catalog, data["cards"], text,
                             self.picture_of, guard=True)
        update_rules(lambda d: d["clusters"].__setitem__(key, rec))
        self.log("rule %s (%d cards): mode %s, %d valid questions, %s ms%s"
                 % (key, len(slugs), rec["mode"],
                    sum(1 for q in rec.get("questions") or [] if q["valid"]),
                    rec.get("ms", "-"), "  ERROR " + rec["error"] if rec["error"] else ""))
        return rec, True
