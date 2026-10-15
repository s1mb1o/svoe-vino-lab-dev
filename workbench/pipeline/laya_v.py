"""Read Jev choice probabilities for the Workbench option-score reranker.

The image runtime uses POST /v1/systemone. It does not generate chat tokens.
Only the option-score schema is supported. Other VLM tasks MUST use a chat entry.
"""
import json
import math
import re
import time
import urllib.error
import urllib.request

import model_cache

VERSION = 1
CONTEXT = ("Read only visible evidence in the supplied label image. "
           "Do not select a wine. Use other for a visible value outside the criteria. "
           "Use not visible for absent or unreadable evidence.")


class LayaVError(Exception):
    """The typed request or response cannot contribute rerank evidence."""


def request_payload(content, schema):
    """Translate the existing score prompt and schema into typed choice questions."""
    images = [part.get("image_url", {}).get("url") for part in content
              if part.get("type") == "image_url"]
    if len(images) != 1 or not isinstance(images[0], str) or not images[0].startswith(
            "data:image/"):
        raise LayaVError("Laya-V reranking requires one image data URI")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise LayaVError("Laya-V supports the cluster option-score schema only")
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise LayaVError("Laya-V requires at least one option-score question")
    if (schema.get("additionalProperties") is not False
            or set(schema.get("required", [])) != set(properties)):
        raise LayaVError("Laya-V requires a complete option-score schema")
    prompt = "\n".join(part.get("text", "") for part in content
                       if part.get("type") == "text")
    questions, options = {}, {}
    for qid, prop in properties.items():
        scores = prop.get("properties", {})
        if (prop.get("type") != "object" or not scores
                or set(prop.get("required", [])) != set(scores)
                or prop.get("additionalProperties") is not False
                or any(value != {"type": "integer", "minimum": 0, "maximum": 100}
                       for value in scores.values())
                or "other" not in scores or "not visible" not in scores):
            raise LayaVError("Laya-V supports the cluster option-score schema only")
        match = re.search(r"^" + re.escape(qid) + r": (.*?)\nOptions:", prompt, re.M | re.S)
        if match is None:
            raise LayaVError("Laya-V cannot find the question text for %s" % qid)
        options[qid] = {"o%d" % i: option for i, option in enumerate(scores)}
        questions[qid] = {"type": "choice", "instructions": match.group(1) + " " + CONTEXT,
                          "criteria": options[qid]}
    return {"state": {"image": images[0], "image_detail": "mid", "context": CONTEXT},
            "questions": questions}, options


def _number(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and 0 <= value <= 1)


def scores_of(body, options, expected_model="laya-v"):
    """Check the complete Jev response. Round each distribution to a total of 100."""
    if (not isinstance(body, dict) or set(body) != {"model", "answers", "usage"}
            or body.get("model") != expected_model):
        raise LayaVError("Laya-V returned an invalid response envelope")
    usage = body["usage"]
    if (not isinstance(usage, dict) or set(usage) != {"input_tokens", "output_tokens"}
            or any(isinstance(v, bool) or not isinstance(v, int) or v < 0
                   for v in usage.values())):
        raise LayaVError("Laya-V returned invalid token usage")
    answers = body["answers"]
    if not isinstance(answers, dict) or set(answers) != set(options):
        raise LayaVError("Laya-V returned missing or extra question IDs")
    result = {}
    for qid, criteria in options.items():
        answer = answers[qid]
        if (not isinstance(answer, dict)
                or set(answer) != {"type", "choice", "probabilities", "confidence"}
                or answer.get("type") != "choice"):
            raise LayaVError("Laya-V returned an invalid choice for %s" % qid)
        probs = answer["probabilities"]
        if (not isinstance(probs, dict) or set(probs) != set(criteria)
                or any(not _number(value) for value in probs.values())):
            raise LayaVError("Laya-V returned invalid probabilities for %s" % qid)
        total = sum(probs.values())
        # The service rounds each probability to four decimal places.
        tolerance = len(criteria) * 0.00005 + 1e-8
        if total <= 0 or abs(total - 1) > tolerance:
            raise LayaVError("Laya-V probabilities MUST total 1 for %s" % qid)
        choice, confidence = answer["choice"], answer["confidence"]
        if (not isinstance(choice, str) or choice not in criteria
                or not _number(confidence)
                or max(probs.values()) - probs[choice] > 0.0001):
            raise LayaVError("Laya-V returned an inconsistent choice for %s" % qid)
        scaled = {key: probs[key] * 100 / total for key in criteria}
        rounded = {key: math.floor(value) for key, value in scaled.items()}
        remainder = 100 - sum(rounded.values())
        order = sorted(criteria, key=lambda key: -(scaled[key] - rounded[key]))
        for key in order[:remainder]:
            rounded[key] += 1
        result[qid] = {option: rounded[key] for key, option in criteria.items()}
    return result


def post(entry, payload, timeout):
    """Send one request. The reranker retains its validation retry and failure policy."""
    headers = {"Content-Type": "application/json"}
    if entry.key_env:
        key = entry.api_key()
        if not key:
            raise LayaVError("the environment variable %s is not set" % entry.key_env)
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(entry.url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        raise LayaVError("Laya-V HTTP %d" % status) from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise LayaVError("no valid answer from Laya-V: %s" % exc) from exc


def ask(entry, content, timeout, schema, cache_read=True, cache_validator=None):
    """Return the existing VLM result fields from a validated typed decision."""
    payload, options = request_payload(content, schema)
    # Reuse the image-aware cache key builder. Store the original Jev answer.
    cache_payload = {"model": entry.model, "messages": [{"role": "user", "content": content}],
                     "response_format": {"schema": schema}, "laya_v_adapter": VERSION,
                     "image_detail": payload["state"]["image_detail"],
                     "questions": payload["questions"], "context": CONTEXT}
    fields = model_cache.vlm_fields(entry.url, cache_payload)
    record = model_cache.lookup(fields) if fields and cache_read else None
    if record is None:
        started = time.perf_counter()
        body = post(entry, payload, timeout)
        ms, cached = (time.perf_counter() - started) * 1000, False
    else:
        body, ms, cached = record["answer"], record["ms"], True
    scores = scores_of(body, options)
    if cache_validator is not None and not cache_validator(scores):
        raise LayaVError("Laya-V scores failed the rerank validator")
    if fields and not cached:
        model_cache.store(fields, body, ms)
    return {"text": json.dumps(scores, ensure_ascii=False), "ms": round(ms),
            "usage": body["usage"], "finish_reason": "stop", "model": body["model"],
            "cached": cached}
