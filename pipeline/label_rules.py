"""The label rules of the embedding clusters. Read docs/plans/45_cluster-label-rules.md.

Stage 1 asks a VLM to describe the label of each card of a cluster. The call sends the
package cut of the effective main image of the card, scaled UP or down to
`describe_side`, and no card data. So the description holds what the model sees.
Obvious key drift of an answer gets the key of the prompt, for example `text` -> `texts`
(`label_descriptions.repair`, plan 61). The record keeps the renames in `repairs`.

Stage 2 asks a VLM where the labels of one cluster differ. The call sends one image for
each card (its label cut), the card data, the stage 1 descriptions, and the note of the
reviewer. The answer is a difference sheet, which holds questions with the expected
answer of each card, and a rule text. The code checks the sheet and sets the mode:

    sheet    at least one question separates two cards
    verdict  no question separates two cards, and the rule text is not empty and
             names no feature outside the label
    none     neither

The prompts and the check are a port of `svoe-vino-testset/scripts/cluster_rules.py`
(plans 05 and 06 of `svoe-vino-testset`). The lab copy `scripts/cluster_rules.py` holds
the same prompt texts, and a test compares them. The prompts are sent as they are
written here. Do not translate them.

The file `data/embeddings/<name>/cluster-rules.json` holds the descriptions under
`cards` (by slug) and the rules under `spaces.label` (by cluster key). The rules are for
the clusters of the view `combined`; the rule space is `label`, because the matcher
sends a label crop at query time (plans 30 and 43). `clusters.load_rules` reads `spaces`.
"""
import base64
import concurrent.futures
import contextlib
import fcntl
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

from PIL import Image, ImageOps

import clusters
import embeddings
import label_descriptions
import model_cache
import vlm_config

VERSION = 1
VIEW = "combined"
RULE_SPACE = "label"
LOCK = "cluster-rules.json.lock"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# The block `label_rules` of `config.yaml`. A missing key takes the value of this
# dictionary. `rules_vlm` None takes the entry of `vlm`. The comments of the block in
# `config.yaml` explain each key.
CONFIG_KEY = "label_rules"
CONFIG_DEFAULTS = {
    "vlm": "qwen3.5-9b-nvfp4", "thinking": False, "describe_side": 2048,
    "describe_max_tokens": 1500, "describe_workers": 4, "timeout_s": 300,
    "rules_vlm": None, "rules_thinking": False, "rules_max_side": 768,
    "rules_max_images": 20, "rules_max_tokens": 2500, "rules_context_tokens": 32768,
    "rules_workers": 2, "rules_timeout_s": 300,
}
# The smallest value of each integer key.
INT_KEYS = {"describe_side": 64, "describe_max_tokens": 1, "describe_workers": 1,
            "rules_max_side": 64, "rules_max_images": 1, "rules_max_tokens": 1,
            "rules_context_tokens": 2, "rules_workers": 1}
# The prompt estimate of stage 2 keeps this room below `rules_context_tokens` and the
# answer.
CONTEXT_MARGIN = 1024
# A second attempt for an answer that reached `max_tokens`: with temperature 0 the same
# request loops again. The service of `qwen3.5-9b-nvfp4` (vLLM) accepts the key
# (probe of 2026-09-26).
REPETITION_PENALTY = 1.15

DESCRIBE_PROMPT = (
    "This is a catalogue photo of one wine bottle. Describe its label, so that a "
    "person can tell this bottle apart from similar bottles of the same producer.\n"
    "Report only what you see. Do not guess. If a text or a number is too small to "
    "read, write \"unreadable\" for it.\n"
    "Write each text exactly as it is printed, in its own alphabet. Do not "
    "translate it and do not transliterate it.\n"
    "Answer with one JSON object with these keys:\n"
    "\"texts\": a list of every text that you can read, each as {\"text\": "
    "\"...\", \"where\": \"...\"};\n"
    "\"numbers\": a list of every number that you can read, such as a year, a "
    "ratio or a percentage, each as {\"value\": \"...\", \"where\": \"...\"};\n"
    "\"vintage\": the vintage year if the label shows one, else null;\n"
    "\"colours\": the main colours of the label;\n"
    "\"design\": a short description of the design and the layout of the label;\n"
    "\"marks\": a list of stickers, medals, seals and other marks, each with its "
    "place;\n"
    "\"bottle\": the colour and the shape of the bottle and of the capsule."
)

RULES_PROMPT = (
    "You see the label pictures of %(n)d wine cards, Card A to Card %(last)s. Each "
    "picture shows the label of the catalogue picture of one card. A recognizer "
    "confuses these cards, because their bottles look alike. Some catalogue "
    "pictures are drawings, not photos. In a drawing, only the label is drawn "
    "correctly.\n"
    "\n"
    "The catalogue data and the label description of each card:\n"
    "\n"
    "%(cards)s\n"
    "\n"
    "Notes of the reviewer about these cards:\n"
    "%(notes)s\n"
    "\n"
    "Task: find the features of the label that tell the cards apart. Later, a "
    "model will look at the label of a customer photo of ONE of these bottles and "
    "answer your questions. That model sees only the label. The answers MUST "
    "identify the card.\n"
    "\n"
    "Rules:\n"
    "1. Write 1 to 3 short questions about the label. A person MUST be able to "
    "answer each question by looking at the label alone.\n"
    "1a. Use only features that are printed on the label. Do not ask about the "
    "glass, the colour of the liquid, the capsule, the cork or the shape of the "
    "bottle.\n"
    "2. Use only MAJOR differences between the wines: the grape varieties, a "
    "kosher mark, the wine name or the name of the line, the colour of the wine as "
    "the label states it (red, white, rose, orange), the sugar level (brut, extra "
    "brut, dry, semi-dry, semi-sweet, sweet), a blend ratio, a reserve or special "
    "edition mark, the volume of the bottle, and the vintage year under rule 2a. A "
    "different design, colour shade, background, font or pattern is NOT a major "
    "difference. Do not use it, unless the notes of the reviewer name it.\n"
    "2a. Ask about the vintage year only when the catalogue names of at least two "
    "cards state two different years. Take the expected year of each card from its "
    "name, and give null to a card whose name states no year. A year that only the "
    "picture shows is not a feature of the card, because the next bottle of the "
    "same wine can show the next vintage.\n"
    "3. For each question, give the expected answer of each card as a short text, "
    "such as \"2019\", \"30/70\" or \"brut\". Give null when the label of the card "
    "does not show this feature. Write a name, a grape variety or another text "
    "exactly as the label prints it, in its own alphabet. Do not translate it and "
    "do not transliterate it. When the picture of a card is the picture of another "
    "card, write the text as the catalogue data of the card writes it. Give a "
    "sugar level or a colour of the wine with the words of rule 2.\n"
    "3a. A mark that only some cards carry, such as a kosher mark or a reserve "
    "mark, gets a yes/no question, for example \"Does the label show a kosher "
    "mark?\". Give \"yes\" or \"no\" for each card, and not null.\n"
    "4. Use a question only when at least two cards have different answers.\n"
    "5. The notes of the reviewer are correct. Use them first.\n"
    "6. Do not use a bottle number, a batch number, a lot number or a serial "
    "number, such as «Бут. №» or «Тираж». These numbers change from bottle to "
    "bottle.\n"
    "7. The catalogue data is correct. A catalogue picture can be too small to "
    "show a small text. Then take the value from the catalogue data, for example a "
    "year, a grape or a ratio in the name.\n"
    "8. A model wrote the label descriptions, and they can hold errors. Use a "
    "feature only when you see it in the pictures, or when the catalogue data or "
    "the notes of the reviewer state it.\n"
    "9. Two texts that differ only by their alphabet, such as ФАНТОМ and PHANTOM, "
    "are the same text and are not a difference.\n"
    "10. The alcohol value can change between two vintages of one wine. Use it "
    "only when no other feature differs.\n"
    "11. List the groups of cards that no major feature tells apart in "
    "\"indistinguishable\".\n"
    "12. Also write the rule as one short plain text, for example: \"If the label "
    "shows 30/70, it is card A; otherwise it is card B.\"\n"
    "\n"
    "Answer with one JSON object:\n"
    "{\"differences\": \"where the labels differ\", \"questions\": [{\"question\": "
    "\"...\", \"answers\": {\"A\": \"...\", \"B\": null}}], \"rule\": \"...\", "
    "\"indistinguishable\": [[\"A\", \"B\"]]}"
)

CARD_BLOCK = (
    "Card %(letter)s: name \"%(name)s\"; producer \"%(producer)s\"; category "
    "\"%(category)s\"; grapes \"%(grapes)s\"; alcohol %(alcohol)s (the number at "
    "the end of the catalogue slug).\n"
    "Label description of card %(letter)s: %(description)s"
)

# The caption before the picture of each card in stage 2. The catalogue reuses the
# picture of one card for another card; the caption names the cards that share it.
CAPTION = "Card %(letter)s:"
CAPTION_NO_LABEL = ("Card %(letter)s (the whole catalogue picture, because no label crop "
                    "exists):")
CAPTION_SHARED = (
    "Card %(letter)s (the same catalogue picture as card %(twins)s. The catalogue "
    "can reuse the picture of another card. Where the picture contradicts the "
    "catalogue data of card %(letter)s, take the answers of card %(letter)s from "
    "its catalogue data):"
)

# The vintage variants of plan 06 of `svoe-vino-testset`. Only the prompt of a cluster
# that holds cards that state a year and cards that state none gets this note.
VINTAGE_NOTE = (
    "Vintage variants. The catalogue data or the label descriptions state a "
    "vintage year for these cards: %(dated)s. They state no vintage year for these "
    "cards: %(undated)s. Check these years in the pictures. When a card that "
    "states no year and one or more cards that state a year differ only by the "
    "vintage year, rule 2a does not apply to them. Then ask a vintage question. "
    "Give each card that states a year that year. Give each card that states no "
    "year the answer \"other\": it is the card of every vintage that no other card "
    "states. When the cards differ by more than the vintage year, follow rule 2a."
)
# The answer of a card that states no year. The matcher holds the same word.
OTHER = "other"
NO_PHOTO = "(no catalogue photo)"
NO_PICTURE = "no catalogue picture"
FILE_NOTE = ("Label descriptions and cluster rules of one embedding. "
             "pipeline/build_label_rules.py writes this file. Read "
             "docs/plans/45_cluster-label-rules.md.")

ALCOHOL = re.compile(r"-(\d{2,3})$")
# A question about a number that changes from bottle to bottle.
SERIAL = re.compile(r"serial|batch|\blot\b|bottle number|бут\.?\s*№|тираж|№")
# A question or a rule text about a feature outside the label.
BOTTLE = re.compile(r"glass|liquid|through the|capsule|cork|neck foil|foil capsule|"
                    r"shape of the bottle|bottle shape|colou?r of the bottle|"
                    r"bottle colou?r|wine in the bottle|стекл|капсул|пробк")
ALCOHOL_WORDS = re.compile(r"alcohol|abv|% ?vol|алкогол|крепост")
PERCENT = re.compile(r"^\d{1,2}([.,]\d{1,2})?\s*%")
# `\byear\b` does not take «years», so a question about the years of ageing stays a
# `feature`.
VINTAGE_WORDS = re.compile(r"vintage|harvest|урож|\byear\b")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
# The answers that state no value. `svoe-vino-matcher/svm/cluster_rules.py` holds the
# same list.
NOT_VISIBLE = {"", "null", "none", "n/a", "not visible", "not shown", "unreadable",
               "unknown", "не видно"}
# The message of vLLM for a prompt with too many images, for example
# `At most 1 image(s) may be provided in one prompt.`
IMAGE_LIMIT = re.compile(r"At most (\d+) image\(s\) may be provided in one prompt")


class RuleError(RuntimeError):
    """The configuration, the files, or the run do not allow the work."""


class VlmError(RuntimeError):
    """One VLM call failed."""


class ImageLimitError(VlmError):
    """The service refused the number of images of one prompt."""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha(value, length=16):
    return clusters.sha256_json(value)[:length]


# ---------------------------------------------------------------- the configuration

def config_values(settings):
    """Return the checked block `label_rules` of `config.yaml`, with the two VLM entries
    as `entry` and `rules_entry`. Raise RuleError."""
    try:
        _, config, _ = embeddings.read_config(settings.config_path)
    except embeddings.ConfigError as exc:
        raise RuleError(str(exc)) from exc
    block = config.get(CONFIG_KEY)
    if block is None:
        block = {}
    if not isinstance(block, dict):
        raise RuleError("the key `%s` of config.yaml MUST be a mapping" % CONFIG_KEY)
    unknown = sorted(set(block) - set(CONFIG_DEFAULTS))
    if unknown:
        raise RuleError("%s: unknown key: %s" % (CONFIG_KEY, ", ".join(unknown)))
    values = {**CONFIG_DEFAULTS, **block}
    if values["rules_vlm"] is None:
        values["rules_vlm"] = values["vlm"]
    for key in ("thinking", "rules_thinking"):
        if not isinstance(values[key], bool):
            raise RuleError("%s.%s MUST be true or false" % (CONFIG_KEY, key))
    for key, low in INT_KEYS.items():
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < low:
            raise RuleError("%s.%s MUST be an integer of at least %d" % (CONFIG_KEY, key, low))
    for key in ("timeout_s", "rules_timeout_s"):
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise RuleError("%s.%s MUST be a positive number of seconds" % (CONFIG_KEY, key))
    if values["rules_context_tokens"] <= values["rules_max_tokens"] + CONTEXT_MARGIN:
        raise RuleError("%s.rules_context_tokens MUST be more than rules_max_tokens + %d"
                        % (CONFIG_KEY, CONTEXT_MARGIN))
    try:
        values["entry"] = vlm_config.entry(config, values["vlm"])
        values["rules_entry"] = vlm_config.entry(config, values["rules_vlm"])
    except vlm_config.VlmConfigError as exc:
        raise RuleError("%s: %s" % (CONFIG_KEY, exc)) from exc
    values["describe_sha"] = sha({
        "prompt": DESCRIBE_PROMPT, "vlm": values["entry"].name,
        "model": values["entry"].model, "thinking": values["thinking"],
        "side": values["describe_side"]})
    values["rules_sha"] = sha({
        "prompt": RULES_PROMPT, "card": CARD_BLOCK,
        "captions": [CAPTION, CAPTION_NO_LABEL, CAPTION_SHARED], "vintage": VINTAGE_NOTE,
        "vlm": values["rules_entry"].name, "model": values["rules_entry"].model,
        "thinking": values["rules_thinking"], "max_side": values["rules_max_side"]})
    return values


# ---------------------------------------------------------------- the pictures

def picture_png(path, side):
    """Return (PNG bytes, size): the picture upright, on white, scaled UP or down to the
    long side `side`. The service gets no transparency."""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            white = Image.new("RGB", image.size, "white")
            white.paste(image, mask=image.getchannel("A"))
            image = white
        else:
            image = image.convert("RGB")
    if max(image.size) != side:
        scale = side / max(image.size)
        image = image.resize((max(1, round(image.width * scale)),
                              max(1, round(image.height * scale))), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue(), image.size


def data_url(png):
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def image_tokens(size):
    """An estimate of the tokens of one picture: one token for each 32 x 32 pixels."""
    return math.ceil(size[0] / 32) * math.ceil(size[1] / 32) + 4


def card_pictures(wine, sources):
    """Return the pictures of one card as (stage 1, stage 2), or (None, None).

    The effective main image is the first column of `main_patched` or `main`
    (`embeddings.read_inputs` puts `main_patched` first and drops the replaced `main`).
    Stage 1 sends its `package` cut, else the original. Stage 2 sends its `label` cut;
    a card with no label cut sends the stage 1 picture with `CAPTION_NO_LABEL`."""
    if not wine:
        return None, None
    main = next((digest for image_type, digest in wine["columns"]
                 if image_type in ("main_patched", "main")), None)
    source = sources.get(main) if main else None
    if not source:
        return None, None
    cuts = source.get("cuts") or {}
    package, label = cuts.get("package"), cuts.get("label")
    first = ({"kind": "package", "sha256": package["sha256"], "path": package["path"]}
             if package else {"kind": "original", "sha256": main, "path": source["path"]})
    second = ({"kind": "label", "sha256": label["sha256"], "path": label["path"]}
              if label else dict(first))
    for picture in (first, second):
        picture["source_sha256"] = main
    return first, second


# ---------------------------------------------------------------- the VLM

def image_limit_message(entry, allowed, sent):
    return ("the service of the vlm entry %s accepts at most %s image(s) in one prompt, "
            "and stage 2 sends one image for each card (%d here). Raise the option "
            "--limit-mm-per-prompt of the service, or set %s.rules_max_images to the "
            "limit of the service: then a larger cluster gets an error record and no call"
            % (entry.name, allowed, sent, CONFIG_KEY))


def post(entry, payload, timeout, retries=3):
    """Send one chat request. Return the decoded body. Raise VlmError, or
    ImageLimitError when the service refuses the number of images."""
    headers = {"Content-Type": "application/json"}
    if entry.key_env:
        key = entry.api_key()
        if not key:
            raise VlmError("the environment variable %s is not set" % entry.key_env)
        headers["Authorization"] = "Bearer " + key
    body = json.dumps(payload).encode("utf-8")
    sent = sum(1 for message in payload["messages"] for part in message["content"]
               if isinstance(part, dict) and part.get("type") == "image_url")
    delay, last = 5.0, "no answer"
    for attempt in range(retries):
        request = urllib.request.Request(entry.url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", "replace")
            exc.close()
            limit = IMAGE_LIMIT.search(text)
            if exc.code == 400 and limit:
                raise ImageLimitError(image_limit_message(entry, limit.group(1), sent))
            last = "HTTP %d: %.300s" % (exc.code, text)
            if exc.code != 429 and exc.code < 500:
                break           # another 4xx does not change on a second attempt
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last = "no answer from %s: %s" % (entry.url, exc)
        if attempt + 1 < retries:
            time.sleep(delay)
            delay *= 2
    raise VlmError(last)


def parse_json(text):
    """The JSON object of an answer, or None."""
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        match = re.search(r"\{.*\}", text or "", re.S)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
        except ValueError:
            return None
    return value if isinstance(value, dict) else None


def ask(entry, content, max_tokens, thinking, timeout, extra=None, schema=None):
    """Send one user message with JSON mode and temperature 0. Return a dict: `text`,
    `ms`, `usage`, `finish_reason`, `model`, `cached`. `schema`, when set, asks the
    service to keep to that JSON Schema (`json_schema`), as the verdict of the cluster
    re-rank does (plan 48).

    A call that repeats an earlier complete answer reads `model_cache`. A record is
    stored only for an answer that holds a JSON object and that `max_tokens` did not cut
    off."""
    response_format = {"type": "json_object"} if schema is None else {
        "type": "json_schema", "json_schema": {"name": "answer", "schema": schema}}
    payload = {"model": entry.model, "temperature": 0, "max_tokens": max_tokens,
               "response_format": response_format,
               "messages": [{"role": "user", "content": content}]}
    if entry.thinking_field == "top_level":
        payload["enable_thinking"] = thinking
    else:
        payload["chat_template_kwargs"] = {"enable_thinking": thinking}
    payload.update(extra or {})
    fields = model_cache.vlm_fields(entry.url, payload)
    record = model_cache.lookup(fields) if fields else None
    if record is not None:
        body, ms, cached = record["answer"], record["ms"], True
    else:
        started = time.perf_counter()
        body = post(entry, payload, timeout)
        ms, cached = (time.perf_counter() - started) * 1000, False
    try:
        choice = body["choices"][0]
        text = (choice["message"].get("content") or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        raise VlmError("the body holds no answer: %.300s" % json.dumps(body))
    finish = choice.get("finish_reason")
    if not cached and fields and finish != "length" and parse_json(text) is not None:
        model_cache.store(fields, body, ms)
    return {"text": text, "ms": round(ms), "usage": body.get("usage") or {},
            "finish_reason": finish, "model": body.get("model") or entry.model,
            "cached": cached}


def ask_guarded(ask_fn, entry, content, max_tokens, thinking, timeout, limit=None):
    """Call `ask_fn`. An answer that reached `max_tokens` is asked once more with a
    repetition penalty and twice the limit (at most `limit`). Return (answer, guarded)."""
    out = ask_fn(entry, content, max_tokens, thinking, timeout)
    if out["finish_reason"] != "length":
        return out, False
    retry = max_tokens * 2 if limit is None else min(max_tokens * 2, limit)
    return ask_fn(entry, content, retry, thinking, timeout,
                  extra={"repetition_penalty": REPETITION_PENALTY}), True


def answer_record(out, guarded):
    rec = {"ms": out["ms"], "usage": out["usage"], "model": out["model"],
           "cached": out["cached"], "finish_reason": out["finish_reason"]}
    if guarded:
        rec["loop_guard"] = {"repetition_penalty": REPETITION_PENALTY}
    return rec


# ---------------------------------------------------------------- stage 1

def description_current(rec, picture, cfg):
    """True when the description `rec` belongs to `picture` and to the settings."""
    return bool(rec and not rec.get("error") and picture
                and rec.get("picture_sha256") == picture["sha256"]
                and rec.get("settings_sha") == cfg["describe_sha"])


def describe(ask_fn, cfg, picture):
    """Stage 1 for one card. Return the description record."""
    entry = cfg["entry"]
    rec = {"source_sha256": picture["source_sha256"], "picture_sha256": picture["sha256"],
           "picture_kind": picture["kind"], "settings_sha": cfg["describe_sha"],
           "vlm": entry.name, "built_at": now(), "description": None, "error": None}
    try:
        png, size = picture_png(picture["path"], cfg["describe_side"])
    except OSError as exc:
        rec["error"] = "cannot read the picture %s: %s" % (picture["path"], exc)
        return rec
    rec["sent_size"] = list(size)
    content = [{"type": "image_url", "image_url": {"url": data_url(png)}},
               {"type": "text", "text": DESCRIBE_PROMPT}]
    try:
        out, guarded = ask_guarded(ask_fn, entry, content, cfg["describe_max_tokens"],
                                   cfg["thinking"], cfg["timeout_s"])
    except VlmError as exc:
        rec["error"] = str(exc)
        return rec
    rec.update(answer_record(out, guarded))
    value = parse_json(out["text"])
    if value is None or out["finish_reason"] == "length":
        rec["error"] = ("the answer is not a JSON object (finish_reason %s)"
                        % out["finish_reason"])
        rec["raw"] = out["text"][:4000]
    else:
        # Plan 61: obvious key drift gets the key of the prompt. The stored descriptions
        # of earlier runs keep their keys (owner answer of 2026-09-27T14:46:48+0300).
        value, renames = label_descriptions.repair(value)
        if renames:
            rec["repairs"] = renames
        rec["description"] = value
    return rec


# ---------------------------------------------------------------- stage 2: the text

def normalize(text):
    """The compared form of an answer, or None for an answer that states no value.

    Lower case, `ё` as `е`, no quotes or end punctuation, no space around `/`, `-`,
    `:` and `%`. `30 / 70` gives `30/70`."""
    if text is None:
        return None
    t = str(text).strip().lower().replace("ё", "е")
    t = t.strip(" \t\n\"'«»`.,;:!?()[]")
    t = re.sub(r"\s*([/\-:%])\s*", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    return None if t in NOT_VISIBLE else t


def alcohol_of(slug):
    """The alcohol value that the slug states, as text, or None. `-145` is 14.5 %."""
    match = ALCOHOL.search(slug or "")
    if not match:
        return None
    digits = match.group(1)
    return (digits if len(digits) == 2 else digits[:2] + "." + digits[2:]) + " %"


def card_data(slug, catalog):
    rec = (catalog or {}).get(slug) or {}
    out = {field: (rec.get(field) or "").strip()
           for field in ("name", "producer", "category", "grapes")}
    out["alcohol"] = alcohol_of(slug)
    return out


def vintage_facts(slugs, catalog, cards):
    """The vintage years that each card states, and the cards that state no year.

    A card states a year in its name, in its slug, or on its label: the key `vintage`
    of its label description. A year of the name or the slug wins over the year of the
    label. A card states no year when its name and its slug hold no year and its
    description gives no vintage. A card with an unreadable or an implausible label
    year, or with no description, is in neither group.

    Return `(dated, undated)`. `dated` maps a slug to `{"years", "where"}`. `undated`
    lists the slugs in the order of `slugs`."""
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


def rules_content(letters, catalog, cards, note_text, pictures, side):
    """Return the message content of stage 2, its token estimate, its prompt text, and
    slug -> the SHA-256 of the file that the request sends for that card.

    Each card goes with its label cut, scaled UP or down to `side`. A card with no
    label cut goes with its stage 1 picture, and its caption states that. The caption of
    a card also names the cards with the same catalogue picture. The key `bottle` of the
    label description stays out: the bottle and the capsule are not on the label."""
    shas = {s: (pictures.get(s) or {}).get("source_sha256") for s in letters.values()}
    content, tokens, blocks, sent = [], 0, [], {}
    for letter, slug in letters.items():
        picture = pictures.get(slug)
        twins = [x for x, s in letters.items()
                 if s != slug and shas[slug] and shas[s] == shas[slug]]
        if not picture or picture["kind"] != "label":
            caption = CAPTION_NO_LABEL % {"letter": letter}
        elif twins:
            caption = CAPTION_SHARED % {"letter": letter, "twins": ", ".join(twins)}
        else:
            caption = CAPTION % {"letter": letter}
        content.append({"type": "text", "text": caption})
        if picture:
            png, size = picture_png(picture["path"], side)
            content.append({"type": "image_url", "image_url": {"url": data_url(png)}})
            tokens += image_tokens(size)
            sent[slug] = picture["sha256"]
        else:
            content.append({"type": "text", "text": NO_PHOTO})
        data = card_data(slug, catalog)
        desc = ((cards or {}).get(slug) or {}).get("description")
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
    return content, tokens + int(len(text) / 2.5), text, sent


# ---------------------------------------------------------------- stage 2: the check

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
    every year of the answer."""
    if answer is None:
        return None
    years = YEAR.findall(answer)
    name = ((catalog or {}).get(slug) or {}).get("name") or ""
    return answer if years and all(y in name or y in slug for y in years) else None


def vintage_answer(answer, slug, dated, catch_all):
    """The expected answer of a vintage question in a rule with vintage variants.

    A card that states a year keeps a single year of `dated`, as the bare year. A card
    of `catch_all` keeps `other`. Every other answer is None."""
    if answer is None:
        return None
    if slug in catch_all:
        return OTHER if normalize(answer) == OTHER else None
    years = set(YEAR.findall(answer))
    if slug in dated and len(years) == 1 and years <= dated[slug]["years"]:
        return years.pop()
    return None


def check_rule(value, letters, catalog=None, cards=None, sent=None):
    """Check the answer of stage 2 and set the mode. The letters become slugs.

    The code enforces these rules of the prompt, because the model does not always keep
    them:

    - A question about a bottle number is never valid.
    - A question about a feature outside the label is never valid, and a rule text about
      such a feature gives mode `none`, not `verdict`.
    - A vintage question keeps the expected year of a card only when the name or the
      slug of the card states that year.
    - The vintage variants of `VINTAGE_NOTE`: the mark `other` stays only for a card that
      states no year, when no other question separates it from a card with a year.
    - A question about the alcohol value is valid only when no other question is valid.

    `sent` maps a slug to the SHA-256 of the file that stage 2 sent for it. Each question
    gets `evidence`: that SHA-256 for each card with an expected answer (plan 30)."""
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
        q["evidence"] = {s: [sent[s]] for s, a in q["answers"].items()
                         if a is not None and (sent or {}).get(s)}
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


# ---------------------------------------------------------------- stage 2: one rule

def inputs_sha(slugs, catalog, cards, pictures1, pictures2, note_text, cfg):
    """The SHA of every input of stage 2. A different value makes a rule stale.

    The input hash of `clusters.json` is not in it: a cluster build that keeps the
    members keeps the rule."""
    slugs = sorted(slugs)
    letters = {LETTERS[i]: s for i, s in enumerate(slugs[:len(LETTERS)])}
    inputs = {
        "slugs": slugs,
        "cards": {s: card_data(s, catalog) for s in slugs},
        "pictures": {s: [(pictures1.get(s) or {}).get("sha256"),
                         (pictures2.get(s) or {}).get("sha256"),
                         (pictures2.get(s) or {}).get("kind")] for s in slugs},
        "descriptions": {s: clusters.sha256_json(((cards or {}).get(s) or {})
                                                 .get("description")) for s in slugs},
        "note": note_text or "",
        "settings": cfg["rules_sha"],
    }
    vintage = vintage_note(letters, catalog, cards)
    if vintage:
        inputs["vintage_note"] = vintage
    return sha(inputs)


def build_rule(ask_fn, cfg, slugs, catalog, cards, pictures1, pictures2, note_text,
               input_hash):
    """Stage 2 for one cluster. Return the rule record. Raise ImageLimitError when the
    service refuses the number of images."""
    entry = cfg["rules_entry"]
    slugs = sorted(slugs)
    rec = {"key": clusters.cluster_key(slugs), "slugs": slugs, "input_hash": input_hash,
           "inputs_sha": inputs_sha(slugs, catalog, cards, pictures1, pictures2,
                                    note_text, cfg),
           "note": note_text or "", "built_at": now(), "vlm": entry.name,
           "settings_sha": cfg["rules_sha"], "mode": "none", "error": None}
    if len(slugs) > len(LETTERS):
        rec["error"] = "a cluster of %d cards has no letters; the limit is %d" % (
            len(slugs), len(LETTERS))
        return rec
    rec["letters"] = {LETTERS[i]: s for i, s in enumerate(slugs)}
    images = sum(1 for s in slugs if pictures2.get(s))
    if images > cfg["rules_max_images"]:
        rec["error"] = ("the cluster needs %d images, one for each card, and %s."
                        "rules_max_images is %d (the limit of the service of the vlm entry "
                        "%s); the call is not sent" % (images, CONFIG_KEY,
                                                       cfg["rules_max_images"], entry.name))
        return rec
    budget = cfg["rules_context_tokens"] - cfg["rules_max_tokens"] - CONTEXT_MARGIN
    side = cfg["rules_max_side"]
    while True:
        try:
            content, estimate, text, sent = rules_content(
                rec["letters"], catalog, cards, note_text, pictures2, side)
        except OSError as exc:
            rec["error"] = "cannot read a picture: %s" % exc
            return rec
        if estimate <= budget or side <= 256:
            break
        side = int(side * 0.75)
    rec.update(max_side=side, prompt_tokens_estimate=estimate, prompt=text)
    try:
        out, guarded = ask_guarded(ask_fn, entry, content, cfg["rules_max_tokens"],
                                   cfg["rules_thinking"], cfg["rules_timeout_s"],
                                   limit=cfg["rules_context_tokens"] - estimate)
    except ImageLimitError:
        raise
    except VlmError as exc:
        rec["error"] = str(exc)
        return rec
    rec.update(answer_record(out, guarded))
    rec["raw_reply"] = out["text"][:8000]
    value = parse_json(out["text"])
    if value is None or out["finish_reason"] == "length":
        rec["error"] = ("the answer is not a JSON object (finish_reason %s)"
                        % out["finish_reason"])
        return rec
    rec.update(check_rule(value, rec["letters"], catalog, cards, sent))
    rec["answer"] = value
    return rec


def rule_current(rec, sha_value):
    return bool(rec and not rec.get("error") and rec.get("inputs_sha") == sha_value)


# ---------------------------------------------------------------- the file

def load_file(directory):
    data = clusters.read_json(os.path.join(directory, clusters.RULES_FILE), default={}) or {}
    if not isinstance(data, dict):
        raise RuleError("%s MUST hold an object" % clusters.RULES_FILE)
    data.setdefault("version", VERSION)
    data.setdefault("cards", {})
    spaces = data.setdefault("spaces", {})
    spaces.setdefault(RULE_SPACE, {})
    return data


def save_file(directory, data, cfg):
    data["note"] = FILE_NOTE
    data["updated_at"] = now()
    data["settings"] = {
        "vlm": cfg["entry"].name, "thinking": cfg["thinking"],
        "describe_side": cfg["describe_side"], "describe_sha": cfg["describe_sha"],
        "rules_vlm": cfg["rules_entry"].name, "rules_thinking": cfg["rules_thinking"],
        "rules_max_side": cfg["rules_max_side"], "rules_sha": cfg["rules_sha"]}
    data["prompts"] = {"describe": DESCRIBE_PROMPT, "rules": RULES_PROMPT, "card": CARD_BLOCK,
                       "captions": [CAPTION, CAPTION_NO_LABEL, CAPTION_SHARED],
                       "vintage": VINTAGE_NOTE}
    clusters.write_json(os.path.join(directory, clusters.RULES_FILE), data)


# ---------------------------------------------------------------- the run

# The wait of a rebuild for a running build: the time between two tries, and the limit.
LOCK_POLL_S = 2.0
LOCK_MAX_WAIT_S = 3600.0


def log_line(text):
    print(time.strftime("%H:%M:%S ") + text, file=sys.stderr, flush=True)


@contextlib.contextmanager
def rules_lock(directory, name, wait=False):
    """Hold the lock of the rules file of one embedding. Without `wait`, raise
    clusters.Busy when another build holds it. With `wait` (the rebuild after a note
    change), try again every `LOCK_POLL_S` seconds, for at most `LOCK_MAX_WAIT_S`."""
    os.makedirs(directory, exist_ok=True)
    deadline = time.monotonic() + LOCK_MAX_WAIT_S
    with open(os.path.join(directory, LOCK), "a+") as lock:
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if not wait or time.monotonic() >= deadline:
                    raise clusters.Busy("another label rule build of %s runs" % name)
                time.sleep(LOCK_POLL_S)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def run(settings, name, stage="all", cluster_slug=None, force=False, dry_run=False,
        ask_fn=ask, log=log_line, wait_lock=False):
    """Build the descriptions and the rules of one embedding that are not current.
    Return the summary. Raise RuleError, or clusters.Busy when another build runs.

    `stage` is `describe`, `rules`, or `all`. `cluster_slug` limits the work to the
    cluster of that card. `force` builds a current description or rule again. `dry_run`
    lists the work and makes no call and no write. `wait_lock` waits for a running build
    instead of raising clusters.Busy. The run reads its inputs after it holds the lock,
    so a run that waited reads the present files."""
    if stage not in ("describe", "rules", "all"):
        raise RuleError("stage MUST be describe, rules, or all")
    cfg = config_values(settings)
    try:
        directory = embeddings.entry_dir(settings.db_path, settings.find(name).name)
    except (KeyError, ValueError, embeddings.ConfigError) as exc:
        raise RuleError("config.yaml has no valid embedding %s: %s" % (name, exc)) from exc
    with rules_lock(directory, name, wait_lock):
        return _run(settings, name, cfg, directory, stage, cluster_slug, force, dry_run,
                    ask_fn, log)


def _run(settings, name, cfg, directory, stage, cluster_slug, force, dry_run, ask_fn, log):
    """`run` while the lock is held."""
    started = time.perf_counter()
    try:
        ctx = clusters.context(settings, name)
    except clusters.ClusterError as exc:
        raise RuleError(str(exc)) from exc
    artifact = clusters.load_artifact(directory)
    if artifact is None:
        raise RuleError("embedding %s has no %s; build the clusters first"
                        % (name, clusters.CLUSTERS_FILE))
    chosen = list(((artifact.get("spaces") or {}).get(VIEW) or {}).get("clusters") or [])
    if cluster_slug:
        chosen = [c for c in chosen if cluster_slug in c["slugs"]]
        if not chosen:
            raise RuleError("no %s cluster holds the card %s" % (VIEW, cluster_slug))
    wines = {wine["slug"]: wine for wine in ctx["wines"]}
    slugs = sorted({s for c in chosen for s in c["slugs"]})
    pictures1, pictures2 = {}, {}
    for slug in slugs:
        first, second = card_pictures(wines.get(slug), ctx["sources"])
        if first:
            pictures1[slug], pictures2[slug] = first, second
    catalog = {slug: {"name": rec.get("name"), "producer": rec.get("producer"),
                      "category": rec.get("category"), "grapes": rec.get("grapes")}
               for slug, rec in ctx["catalog"].items()}
    _, notes = clusters.load_notes(directory)
    summary = {"embedding": name, "file": os.path.join(directory, clusters.RULES_FILE),
               "artifact_built_at": artifact.get("built_at"),
               "artifact_stale": artifact.get("input_hash") != ctx["input_hash"],
               "clusters": len(chosen), "cards": len(slugs), "dry_run": dry_run,
               "describe": {"todo": 0, "calls": 0, "cache_hits": 0, "errors": 0},
               "rules": {"todo": 0, "calls": 0, "cache_hits": 0, "errors": 0,
                         "restamped": 0, "modes": {}}}
    guard = threading.Lock()
    data = load_file(directory)

    def store(section, key, rec):
        with guard:
            target = data["cards"] if section == "cards" else data["spaces"][RULE_SPACE]
            target[key] = rec
            save_file(directory, data, cfg)

    # Stage 1.
    if stage in ("describe", "all"):
        todo = [s for s in slugs if s in pictures1 and (
            force or not description_current(data["cards"].get(s), pictures1[s], cfg))]
        missing = [s for s in slugs if s not in pictures1
                   and (data["cards"].get(s) or {}).get("error") != NO_PICTURE]
        if not dry_run:
            for s in missing:
                store("cards", s, {"description": None, "built_at": now(),
                                   "error": NO_PICTURE})
        summary["describe"]["todo"] = len(todo)
        if not dry_run and todo:
            def one(slug):
                rec = describe(ask_fn, cfg, pictures1[slug])
                store("cards", slug, rec)
                return slug, rec
            with concurrent.futures.ThreadPoolExecutor(cfg["describe_workers"]) as pool:
                for slug, rec in pool.map(one, todo):
                    summary["describe"]["calls"] += not rec.get("cached")
                    summary["describe"]["cache_hits"] += bool(rec.get("cached"))
                    summary["describe"]["errors"] += bool(rec["error"])
                    log("describe %s: %s ms%s%s" % (
                        slug, rec.get("ms", "-"), " (cache)" if rec.get("cached") else "",
                        "  ERROR " + rec["error"] if rec["error"] else ""))

    # Stage 2.
    stopped = None
    if stage in ("rules", "all"):
        todo = []
        for cluster in chosen:
            members = sorted(cluster["slugs"])
            note_text = clusters.note_for(cluster, notes).get("text") or ""
            value = inputs_sha(members, catalog, data["cards"], pictures1, pictures2,
                               note_text, cfg)
            old = data["spaces"][RULE_SPACE].get(cluster["key"])
            if not force and rule_current(old, value):
                if old.get("input_hash") != artifact.get("input_hash") and not dry_run:
                    store("rules", cluster["key"],
                          {**old, "input_hash": artifact.get("input_hash")})
                    summary["rules"]["restamped"] += 1
                continue
            todo.append((cluster, members, note_text))
        summary["rules"]["todo"] = len(todo)
        if not dry_run and todo:
            stop = threading.Event()

            def one(item):
                cluster, members, note_text = item
                if stop.is_set():
                    return cluster, None
                try:
                    rec = build_rule(ask_fn, cfg, members, catalog, data["cards"],
                                     pictures1, pictures2, note_text,
                                     artifact.get("input_hash"))
                except ImageLimitError as exc:
                    stop.set()
                    raise RuleError(str(exc)) from exc
                store("rules", cluster["key"], rec)
                return cluster, rec
            with concurrent.futures.ThreadPoolExecutor(cfg["rules_workers"]) as pool:
                futures = [pool.submit(one, item) for item in todo]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        cluster, rec = future.result()
                    except RuleError as exc:
                        stopped = stopped or str(exc)
                        continue
                    if rec is None:
                        continue
                    counts = summary["rules"]
                    counts["calls"] += bool(rec.get("prompt")) and not rec.get("cached")
                    counts["cache_hits"] += bool(rec.get("cached"))
                    counts["errors"] += bool(rec["error"])
                    counts["modes"][rec["mode"]] = counts["modes"].get(rec["mode"], 0) + 1
                    log("rule %s %s (%d cards): mode %s, %d valid questions, %s ms%s%s"
                        % (cluster["id"], cluster["key"], len(rec["slugs"]), rec["mode"],
                           sum(1 for q in rec.get("questions") or [] if q["valid"]),
                           rec.get("ms", "-"), " (cache)" if rec.get("cached") else "",
                           "  ERROR " + rec["error"] if rec["error"] else ""))
    summary["seconds"] = round(time.perf_counter() - started, 1)
    if stopped:
        summary["stopped"] = stopped
    return summary
