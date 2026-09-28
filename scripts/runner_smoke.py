"""Smoke check of the self-hosted GitHub runner of svoe-vino-lab.

The workflow `.github/workflows/runner-smoke.yml` runs this script on the runner
`ct111-svoe-vino-lab-1` (CT 111 on Proxmox x300). The script checks the gx10 services of
the endpoint variables of the runner at three levels:

1. `variables`: each variable is set, and each endpoint is an http(s) URL.
2. `reach`: the TCP port answers, the gateway lists the model in `GET /v1/models`, and
   `GET /running` answers. These two requests load no model.
3. `service`: one real call with a known answer.

The rule "Hybrid" of the Health page applies (owner answer of 2026-09-26T11:02:57+0300):
a real call goes only to a model that runs now, because a request to a model that does not
run makes llama-swap load it, and the load can stop a model that a job uses. Such a service
is `idle`. `idle` is not a failure. `--load-models` sends a real call to each service, so
llama-swap loads the models that do not run (owner answer of 2026-09-28T08:58:00+0300).

Each call sends `Cache-Control: no-cache`. The exact-response cache on port 18082 would
else answer a repeated request without the model.

The script prints no other variable of the environment: the runner environment holds a
secret key. It writes no file, except the job summary of GitHub Actions.

Usage:
    python3 scripts/runner_smoke.py
    python3 scripts/runner_smoke.py --load-models
"""
import argparse
import base64
import io
import math
import os
import random
import socket
import sys
import uuid
from collections import namedtuple
from pathlib import Path
from urllib.parse import urlsplit

import requests
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
BOTTLE = ROOT / "tests" / "data" / "smoke" / "bottle.jpg"
# The bounding box of the bottle in `bottle.jpg`, [x1, y1, x2, y2] in pixels.
BOTTLE_BOX = (97, 50, 304, 923)
MIN_IOU = 0.5

URL_VARIABLES = ("SIGLIP2_ENDPOINT", "GROUNDING_DINO_ENDPOINT", "SAM3_ENDPOINT",
                 "VLM_ENDPOINT", "SHIELDGEMMA_ENDPOINT", "QR_SCANNER_ENDPOINT")
VARIABLES = URL_VARIABLES + ("VLM_MODEL",)
# SIGLIP2_ENDPOINT names no model. The optional variable SIGLIP2_MODEL overrides the
# model of the main embedding of the lab.
DEFAULT_SIGLIP2_MODEL = "siglip2-so400m-patch16-naflex"

LIST_TIMEOUT = 10
CALL_TIMEOUT = 120
# A cold start: sam3 takes 45 to 85 s, the vLLM model of the VLM can take minutes.
LOAD_TIMEOUT = 600
NO_CACHE = {"Cache-Control": "no-cache"}

Service = namedtuple("Service", "name variable url root model check")


class CheckError(Exception):
    """A service gave an answer that the check cannot use."""


class Report:
    """The result rows: (level, name, status, detail). A status is `pass`, `fail`,
    `idle`, or `warn`."""

    def __init__(self, out=None):
        self.rows = []
        self.out = out  # None: the present sys.stdout

    def add(self, level, name, status, detail):
        self.rows.append((level, name, status, detail))
        print("%-4s  %-9s  %-14s  %s" % (status.upper(), level, name, detail),
              file=self.out, flush=True)

    def failed(self):
        return any(row[2] == "fail" for row in self.rows)

    def counts(self):
        counts = {}
        for row in self.rows:
            counts[row[2]] = counts.get(row[2], 0) + 1
        return ", ".join("%d %s" % (n, s) for s, n in sorted(counts.items()))

    def markdown(self, load_models):
        lines = ["## Runner smoke", "",
                 "Load models: %s. Result: %s." % ("yes" if load_models else "no",
                                                   self.counts()), "",
                 "| Level | Name | Status | Detail |", "|---|---|---|---|"]
        for level, name, status, detail in self.rows:
            lines.append("| %s | %s | %s | %s |" % (level, name, status.upper(),
                                                   detail.replace("|", "\\|")))
        return "\n".join(lines) + "\n"


# Level 1: the variables.

def check_variables(env, report):
    """Report each variable. Return the set of the names that are valid."""
    valid = set()
    for name in VARIABLES:
        value = (env.get(name) or "").strip()
        if not value:
            report.add("variables", name, "fail", "not set")
            continue
        if name in URL_VARIABLES:
            parts = urlsplit(value)
            if parts.scheme not in ("http", "https") or not parts.hostname:
                report.add("variables", name, "fail", "not an http(s) URL: %s" % value)
                continue
        report.add("variables", name, "pass", value)
        valid.add(name)
    return valid


def upstream(url):
    """Split `<root>/upstream/<model>` into (root, model)."""
    head, sep, tail = url.rstrip("/").partition("/upstream/")
    if not sep or not tail or "/" in tail:
        raise ValueError("expected <root>/upstream/<model>: %s" % url)
    return head, tail


def services(env, valid, report):
    """Return the services whose variables are valid."""
    specs = [("siglip2", "SIGLIP2_ENDPOINT", check_siglip2),
             ("grounding-dino", "GROUNDING_DINO_ENDPOINT", check_grounding_dino),
             ("sam3", "SAM3_ENDPOINT", check_sam3),
             ("vlm", "VLM_ENDPOINT", check_vlm),
             ("shieldgemma", "SHIELDGEMMA_ENDPOINT", check_shieldgemma),
             ("qr-scanner", "QR_SCANNER_ENDPOINT", check_qr_scanner)]
    result = []
    for name, variable, check in specs:
        if variable not in valid:
            continue
        url = env[variable].strip().rstrip("/")
        try:
            if name == "siglip2":
                root = url
                model = (env.get("SIGLIP2_MODEL") or "").strip() or DEFAULT_SIGLIP2_MODEL
            elif name == "vlm":
                if "VLM_MODEL" not in valid:
                    continue
                if not url.endswith("/v1"):
                    raise ValueError("expected <root>/v1: %s" % url)
                root, model = url[:-len("/v1")], env["VLM_MODEL"].strip()
            else:
                root, model = upstream(url)
        except ValueError as exc:
            report.add("variables", name, "fail", str(exc))
            continue
        result.append(Service(name, variable, url, root, model, check))
    return result


# Level 2: the reachability.

def gateway(root, cache):
    """Return (model ids, {model: state}, error) of the llama-swap gateway `root`."""
    if root not in cache:
        try:
            answer = requests.get(root + "/v1/models", timeout=LIST_TIMEOUT)
            answer.raise_for_status()
            ids = {item["id"] for item in answer.json()["data"]}
            answer = requests.get(root + "/running", timeout=LIST_TIMEOUT)
            answer.raise_for_status()
            states = {item["model"]: item.get("state")
                      for item in answer.json().get("running", [])}
            cache[root] = (ids, states, None)
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            cache[root] = (None, None, "the lists of the gateway %s: %s" % (root, exc))
    return cache[root]


def reach(service, report, cache):
    """Report the reachability. Return (reachable, state of the model or None)."""
    parts = urlsplit(service.root)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        socket.create_connection((parts.hostname, port), timeout=5).close()
    except OSError as exc:
        report.add("reach", service.name, "fail", "TCP %s:%d: %s" % (parts.hostname, port, exc))
        return False, None
    ids, states, error = gateway(service.root, cache)
    if error:
        report.add("reach", service.name, "fail", error)
        return False, None
    if service.model not in ids:
        report.add("reach", service.name, "fail",
                   "%s is not in %s/v1/models" % (service.model, service.root))
        return False, None
    state = states.get(service.model)
    report.add("reach", service.name, "pass", "%s listed; %s" % (
        service.model, "state %s" % state if state else "does not run"))
    return True, state


def action(state, load_models):
    """Return `call`, `idle`, or `warn` for a model in the state `state`."""
    if state == "ready" or load_models:
        return "call"
    return "idle" if state is None else "warn"


# Level 3: the real calls.

def post(url, timeout, **kwargs):
    answer = requests.post(url, timeout=timeout, headers=NO_CACHE, **kwargs)
    if answer.status_code != 200:
        raise CheckError("HTTP %d: %s" % (answer.status_code, answer.text[:200]))
    try:
        return answer.json()
    except ValueError as exc:
        raise CheckError("the answer is not JSON: %s" % exc)


def bottle_file():
    return ("bottle.jpg", BOTTLE.read_bytes(), "image/jpeg")


def bottle_data_url():
    return "data:image/jpeg;base64," + base64.b64encode(BOTTLE.read_bytes()).decode("ascii")


def box_iou(a, b):
    """Return the intersection over union of the boxes [x1, y1, x2, y2]."""
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    if width <= 0 or height <= 0:
        return 0.0
    inter = width * height
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union


def bottle_result(instances, min_score):
    """Judge the best instance of a detection of `bottle` in `bottle.jpg`."""
    if not instances:
        return "fail", "no instance of 'bottle'"
    best = max(instances, key=lambda item: item.get("score") or 0)
    score, iou = best.get("score") or 0, box_iou(best["box"], BOTTLE_BOX)
    status = "pass" if score >= min_score and iou >= MIN_IOU else "fail"
    return status, "bottle score %.2f (min %.2f), IoU %.2f with the known box (min %.2f)" % (
        score, min_score, iou, MIN_IOU)


def check_sam3(service, timeout):
    data = post(service.url + "/segment", timeout, files={"image": bottle_file()},
                data={"text": "bottle", "threshold": "0.5", "return_masks": "false"})
    return bottle_result(data.get("instances") or [], 0.5)


def check_grounding_dino(service, timeout):
    data = post(service.url + "/detect", timeout, files={"image": bottle_file()},
                data={"texts": "bottle", "threshold": "0.3"})
    instances = [item for item in data.get("instances") or []
                 if "bottle" in (item.get("prompt") or item.get("label") or "")]
    return bottle_result(instances, 0.3)


def check_shieldgemma(service, timeout):
    data = post(service.url + "/classify", timeout, files={"image": bottle_file()})
    scores = data.get("scores") or {}
    if not scores:
        raise CheckError("no scores in the answer")
    top = max(scores, key=scores.get)
    flagged = data.get("flagged") or []
    status = "pass" if not flagged and scores[top] < 0.5 else "fail"
    return status, "flagged %s; highest %s %.3f (max 0.5)" % (flagged or "nothing", top,
                                                              scores[top])


# EAN-13: the patterns of the digits, and the parity of the left half by the first digit.
EAN_L = ("0001101", "0011001", "0010011", "0111101", "0100011",
         "0110001", "0101111", "0111011", "0110111", "0001011")
EAN_R = tuple("".join("1" if bit == "0" else "0" for bit in code) for code in EAN_L)
EAN_G = tuple(code[::-1] for code in EAN_R)
EAN_PARITY = ("LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
              "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL")


def ean13(first12):
    """Return the 13 digits of an EAN-13 with the check digit."""
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first12))
    return first12 + str((10 - total % 10) % 10)


def ean13_modules(code):
    """Return the 95 modules of an EAN-13 as a string of 0 and 1."""
    left = "".join((EAN_L if parity == "L" else EAN_G)[int(d)]
                   for parity, d in zip(EAN_PARITY[int(code[0])], code[1:7]))
    right = "".join(EAN_R[int(d)] for d in code[7:])
    return "101" + left + "01010" + right + "101"


def ean13_image(code, module=4, height=160):
    """Draw an EAN-13 with a quiet zone of 11 modules on each side."""
    modules = ean13_modules(code)
    image = Image.new("L", ((len(modules) + 22) * module, height + 40), 255)
    draw = ImageDraw.Draw(image)
    for i, bit in enumerate(modules):
        if bit == "1":
            x = (11 + i) * module
            draw.rectangle([x, 20, x + module - 1, 20 + height], fill=0)
    return image


def check_qr_scanner(service, timeout):
    # The prefix 2 is the range of restricted circulation, so the code is never a product.
    code = ean13("2" + "".join(random.choice("0123456789") for _ in range(11)))
    buffer = io.BytesIO()
    ean13_image(code).save(buffer, "PNG")
    # The engine `zxing-cpp` alone: `auto` can also call SAM3 and a VLM.
    data = post(service.url + "/scan", timeout,
                files={"image": ("ean13.png", buffer.getvalue(), "image/png")},
                data={"engine": "zxing-cpp"})
    texts = [item.get("text") for item in data.get("instances") or []]
    status = "pass" if code in texts else "fail"
    return status, "random EAN-13 %s; decoded %s" % (code, texts or "nothing")


def check_vlm(service, timeout):
    nonce = uuid.uuid4().hex[:8]
    prompt = ("Answer with two words separated by one space. The first word is %s. The "
              "second word is one lowercase English noun that names the main object in "
              "the image." % nonce)
    payload = {"model": service.model, "temperature": 0, "max_tokens": 16,
               "chat_template_kwargs": {"enable_thinking": False},
               "messages": [{"role": "user", "content": [
                   {"type": "image_url", "image_url": {"url": bottle_data_url()}},
                   {"type": "text", "text": prompt}]}]}
    data = post(service.url + "/chat/completions", timeout, json=payload)
    try:
        content = data["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, TypeError):
        raise CheckError("no message in the answer")
    words = content.lower()
    status = "pass" if nonce in words and ("bottle" in words or "wine" in words) else "fail"
    return status, "asked for %s and the object; answer %r" % (nonce, content.strip()[:80])


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def check_siglip2(service, timeout):
    texts = ["a photo of a bottle of wine", "a photo of a cat"]
    data = post(service.url + "/v1/embeddings", timeout,
                json={"model": service.model, "input": [bottle_data_url()] + texts})
    items = sorted(data.get("data") or [], key=lambda item: item.get("index", 0))
    vectors = [item.get("embedding") or [] for item in items]
    if len(vectors) != 3 or len({len(v) for v in vectors}) != 1 or not vectors[0]:
        raise CheckError("expected 3 vectors of one size, got sizes %s"
                         % [len(v) for v in vectors])
    if not all(math.isfinite(x) for v in vectors for x in v):
        raise CheckError("a vector holds a value that is not finite")
    wine, cat = cosine(vectors[0], vectors[1]), cosine(vectors[0], vectors[2])
    status = "pass" if wine > cat else "fail"
    return status, "%s dim %d; image-text cosine: wine %.3f, cat %.3f (wine must be higher)" % (
        service.model, len(vectors[0]), wine, cat)


def serve(service, state, load_models, report):
    """Report the real call of one service, or the reason for no call."""
    step = action(state, load_models)
    if step == "idle":
        report.add("service", service.name, "idle",
                   "%s does not run; not called. Run with --load-models." % service.model)
        return
    if step == "warn":
        report.add("service", service.name, "warn",
                   "%s is in the state %s; not called" % (service.model, state))
        return
    timeout = CALL_TIMEOUT if state == "ready" else LOAD_TIMEOUT
    try:
        status, detail = service.check(service, timeout)
    except requests.Timeout:
        status, detail = "fail", "no answer in %d s" % timeout
    except (requests.RequestException, CheckError) as exc:
        status, detail = "fail", str(exc)
    report.add("service", service.name, status, detail)


def main(argv=None, env=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--load-models", action="store_true",
                        help="call each service; llama-swap loads the models that do not run")
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    report = Report()
    valid = check_variables(env, report)
    cache = {}
    for service in services(env, valid, report):
        reachable, state = reach(service, report, cache)
        if reachable:
            serve(service, state, args.load_models, report)
    print("result: %s" % report.counts())
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(report.markdown(args.load_models))
    return 1 if report.failed() else 0


if __name__ == "__main__":
    sys.exit(main())
