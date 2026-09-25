"""The VLM inferences of the configuration: the key `vlm`.

The key holds a list. One entry is one named VLM inference:

    name            the name that a script uses for the entry; the names differ
    protocol        `openai`: `POST <endpoint>/chat/completions`
    thinking_field  `chat_template_kwargs` or `top_level`: where the switch
                    `enable_thinking` goes in the request
    endpoint        the base URL, for example `http://192.168.86.14:18081/v1`
    model           the model name that the service knows
    key             absent or null (the service needs no key), or `{env:NAME}`: the key
                    is read from the shell variable NAME at run time
    max_tokens      absent (DEFAULT_MAX_TOKENS) or a positive integer: the `max_tokens`
                    of a detail request of `describe_images.py` (owner answer of
                    2026-09-25). The other callers keep their own limits.

Every entry MUST hold the first five keys, MAY hold `key` and `max_tokens`, and MUST hold
no other key.
A key value in the file is refused, so that no key is written into `config.yaml`.

The module imports the standard library alone, so `scripts/` can import it too.
"""
import collections
import os
import re

PROTOCOLS = ("openai",)
THINKING_FIELDS = ("chat_template_kwargs", "top_level")
REQUIRED = ("name", "protocol", "thinking_field", "endpoint", "model")
KEYS = REQUIRED + ("key", "max_tokens")
# The owner chose 8192 on 2026-09-25.
DEFAULT_MAX_TOKENS = 8192

_ENV_KEY = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}\Z")


class VlmConfigError(Exception):
    """The key `vlm` of the configuration cannot be read as it stands."""


class Entry(collections.namedtuple(
        "Entry", "name protocol thinking_field endpoint model key_env max_tokens",
        defaults=(DEFAULT_MAX_TOKENS,))):
    """One VLM inference. `key_env` is the name of the shell variable of the key, or ""
    when the service needs no key."""
    __slots__ = ()

    @property
    def url(self):
        """The chat route of the protocol `openai`."""
        return self.endpoint.rstrip("/") + "/chat/completions"

    def api_key(self):
        """Return the key from the shell, or "" when the entry needs no key or the
        variable is not set."""
        return os.environ.get(self.key_env, "") if self.key_env else ""


def _entry(item, index):
    where = "vlm entry %d" % (index + 1)
    if not isinstance(item, dict):
        raise VlmConfigError("%s MUST be a mapping" % where)
    name = item.get("name")
    if isinstance(name, str) and name.strip():
        where = "vlm entry %s" % name
    missing = [k for k in REQUIRED if k not in item]
    if missing:
        raise VlmConfigError("%s has no key %s" % (where, ", ".join(missing)))
    unknown = sorted(set(item) - set(KEYS))
    if unknown:
        raise VlmConfigError("%s has the unknown key %s" % (where, ", ".join(unknown)))
    for k in ("name", "endpoint", "model"):
        if not isinstance(item[k], str) or not item[k].strip():
            raise VlmConfigError("%s: %s MUST be a text" % (where, k))
    if item["protocol"] not in PROTOCOLS:
        raise VlmConfigError("%s: protocol MUST be one of %s"
                             % (where, ", ".join(PROTOCOLS)))
    if item["thinking_field"] not in THINKING_FIELDS:
        raise VlmConfigError("%s: thinking_field MUST be one of %s"
                             % (where, ", ".join(THINKING_FIELDS)))
    if not item["endpoint"].startswith(("http://", "https://")):
        raise VlmConfigError("%s: endpoint MUST be an http or https URL" % where)
    key = item.get("key")
    if key is None:
        key_env = ""
    else:
        match = _ENV_KEY.match(key) if isinstance(key, str) else None
        if not match:
            # The value is not repeated in the message: it can be a key.
            raise VlmConfigError("%s: key MUST be null or {env:NAME}; never write a key "
                                 "value into the configuration" % where)
        key_env = match.group(1)
    max_tokens = item.get("max_tokens", DEFAULT_MAX_TOKENS)
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
        raise VlmConfigError("%s: max_tokens MUST be a positive integer" % where)
    return Entry(item["name"], item["protocol"], item["thinking_field"],
                 item["endpoint"], item["model"], key_env, max_tokens)


def entries(config):
    """Return the entries of `config["vlm"]` as a dict by name, in file order. A config
    with no key `vlm` gives an empty dict. Raise VlmConfigError for an entry that is not
    valid and for a name that repeats."""
    items = (config or {}).get("vlm")
    if items is None:
        return {}
    if not isinstance(items, list):
        raise VlmConfigError("the key vlm MUST hold a list")
    out = {}
    for index, item in enumerate(items):
        entry = _entry(item, index)
        if entry.name in out:
            raise VlmConfigError("the vlm name %s repeats" % entry.name)
        out[entry.name] = entry
    return out


def entry(config, name):
    """Return the entry `name` of `config["vlm"]`. Raise VlmConfigError when the key
    `vlm` is not valid or holds no entry with this name."""
    found = entries(config).get(name)
    if found is None:
        raise VlmConfigError("the configuration has no vlm entry %s" % name)
    return found
