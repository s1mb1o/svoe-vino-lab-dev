"""Shared VLM request for a pairwise wine-identity check.

The benchmark sends one catalogue reference image and one candidate image. The answer
states whether the candidate shows the same wine. Successful model calls use the shared
model-call cache.
"""

import json
import re
import time
import urllib.request

import model_cache
import vlm_config


PROMPT = (
    "\u041f\u0435\u0440\u0432\u043e\u0435 \u0444\u043e\u0442\u043e \u2014 \u044d\u0442\u0430\u043b\u043e\u043d \u0431\u0443\u0442\u044b\u043b\u043a\u0438 \u0438\u0437 \u043a\u0430\u0442\u0430\u043b\u043e\u0433\u0430. "
    "\u042d\u0442\u043e \u0432\u0438\u043d\u043e: \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \"%s\", \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \"%s\". "
    "\u0412\u0442\u043e\u0440\u043e\u0435 \u0444\u043e\u0442\u043e \u2014 \u0438\u0437 \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u0430.\n"
    "\u041e\u0442\u0432\u0435\u0442\u044c true \u0422\u041e\u041b\u042c\u041a\u041e \u0435\u0441\u043b\u0438 \u043d\u0430 \u0432\u0442\u043e\u0440\u043e\u043c \u0444\u043e\u0442\u043e \u0432\u0438\u0434\u043d\u0430 "
    "\u0431\u0443\u0442\u044b\u043b\u043a\u0430 \u0418\u041c\u0415\u041d\u041d\u041e \u044d\u0442\u043e\u0433\u043e \u0432\u0438\u043d\u0430 \u0441 \u0435\u0433\u043e \u043f\u0435\u0440\u0435\u0434\u043d\u0435\u0439 \u044d\u0442\u0438\u043a\u0435\u0442\u043a\u043e\u0439.\n"
    "\u041e\u0442\u0432\u0435\u0442\u044c false \u0435\u0441\u043b\u0438:\n"
    "- \u0432\u0438\u0434\u043d\u0430 \u0442\u043e\u043b\u044c\u043a\u043e \u0437\u0430\u0434\u043d\u044f\u044f \u044d\u0442\u0438\u043a\u0435\u0442\u043a\u0430 (\u043a\u043e\u043d\u0442\u0440\u044d\u0442\u0438\u043a\u0435\u0442\u043a\u0430) \u0431\u0435\u0437 \u043f\u0435\u0440\u0435\u0434\u043d\u0435\u0439;\n"
    "- \u0432\u0438\u0434\u043d\u0430 \u0442\u043e\u043b\u044c\u043a\u043e \u043f\u0440\u043e\u0431\u043a\u0430, \u043a\u043e\u0440\u043e\u0431\u043a\u0430, \u0431\u043e\u043a\u0430\u043b \u0438\u043b\u0438 \u0447\u0435\u043a;\n"
    "- \u044d\u0442\u043e \u0414\u0420\u0423\u0413\u041e\u0415 \u0432\u0438\u043d\u043e \u0442\u043e\u0433\u043e \u0436\u0435 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044f "
    "(\u0434\u0440\u0443\u0433\u043e\u0439 \u0441\u043e\u0440\u0442, \u0434\u0440\u0443\u0433\u0430\u044f \u0441\u0435\u0440\u0438\u044f, \u0434\u0440\u0443\u0433\u043e\u0439 \u0446\u0432\u0435\u0442);\n"
    "- \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043d\u0435\u043b\u044c\u0437\u044f \u043f\u0440\u043e\u0447\u0438\u0442\u0430\u0442\u044c \u0438 \u044d\u0442\u0438\u043a\u0435\u0442\u043a\u0430 \u0432\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e \u043d\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u0435\u0442 \u0441 \u044d\u0442\u0430\u043b\u043e\u043d\u043e\u043c.\n"
    "\u041e\u0442\u0432\u0435\u0442\u044c \u0442\u043e\u043b\u044c\u043a\u043e JSON: "
    "{\"same_wine\":true|false,\"confidence\":0.0-1.0,\"studio\":true|false,\"front_label\":true|false}"
)

JSON_RE = re.compile(r"\{[^{}]*\}")


def parse(text):
    """Return normalized identity fields from one model answer, or None."""
    match = JSON_RE.search(text or "")
    if not match:
        return None
    try:
        answer = json.loads(match.group(0))
    except (TypeError, ValueError):
        return None
    if "same_wine" not in answer:
        return None
    return {
        "same": 1 if answer.get("same_wine") else 0,
        "conf": float(answer.get("confidence", 0) or 0),
        "studio": 1 if answer.get("studio") else 0,
        "front": 1 if answer.get("front_label") else 0,
    }


def log(message):
    """Write one backend-selection message."""
    print(message, flush=True)


class Backend:
    """One named vision endpoint."""

    def __init__(self, name, url, model, key, workers):
        self.name = name
        self.url = url
        self.model = model
        self.key = key
        self.workers = workers
        self.calls = 0
        self.errors = 0
        self.hits = 0

    def ask(self, ref_url, cand_url, producer, title, timeout=240):
        """Return the model text for one reference and candidate image."""
        payload = {
            "model": self.model,
            "max_tokens": 150,
            "temperature": 0,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": ref_url}},
                {"type": "image_url", "image_url": {"url": cand_url}},
                {"type": "text", "text": PROMPT % (producer, title)},
            ]}],
        }
        fields = model_cache.vlm_fields(self.url, payload)
        record = model_cache.lookup(fields) if fields else None
        if record is not None:
            self.hits += 1
            return record["answer"]["choices"][0]["message"]["content"]
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        request = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(), headers=headers)
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            answer = json.load(response)
        if fields and answer.get("choices"):
            model_cache.store(fields, answer, (time.perf_counter() - started) * 1000)
        return answer["choices"][0]["message"]["content"]


def build_backends(spec, config):
    """Build the comma-separated `name:workers` backend specification."""
    entries = vlm_config.entries(config)
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, worker_count = part.partition(":")
        entry = entries.get(name)
        if entry is None:
            log("unknown backend %s, ignored" % name)
            continue
        key = entry.api_key()
        if entry.key_env and not key:
            log("backend %s has no API key in the environment, ignored" % name)
            continue
        out.append(Backend(name, entry.url, entry.model, key, int(worker_count or 4)))
    return out

