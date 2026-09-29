"""The configuration of the model proxy: one YAML file.

Read docs/plans/01_multi-host-model-proxy.md, section "Configuration". An unknown key is
an error, so that a typing error does not silently change the behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


HOST_KINDS = ("llama-swap", "bootstrap")
_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_SIZE_UNITS = {"kib": 1024, "mib": 1024**2, "gib": 1024**3}


class ConfigError(ValueError):
    """The configuration file breaks a rule."""


@dataclass(frozen=True)
class SshTunnel:
    target: str
    local_port: int
    remote_port: int


@dataclass(frozen=True)
class HostConfig:
    name: str
    kind: str
    url: str
    slots: int
    models: tuple[str, ...]
    enabled: bool = True
    ssh: SshTunnel | None = None


@dataclass(frozen=True)
class ProxyConfig:
    listen_host: str
    listen_port: int
    passthrough: str
    hosts: tuple[HostConfig, ...]
    cache_path: Path
    namespace: str
    ttl_seconds: int
    max_cache_bytes: int
    max_response_bytes: int
    max_request_bytes: int
    queue_limit: int
    queue_timeout: float
    upstream_timeout: float
    attempts: int
    health_interval: float
    health_timeout: float

    @property
    def enabled_hosts(self) -> tuple[HostConfig, ...]:
        return tuple(host for host in self.hosts if host.enabled)

    @property
    def pooled_models(self) -> frozenset[str]:
        """The models that at least one enabled host serves."""
        return frozenset(model for host in self.enabled_hosts for model in host.models)


def parse_size(value: Any, where: str) -> int:
    """Return the bytes of `value`: an integer, or a text such as `256MiB` or `10GiB`."""
    if isinstance(value, bool):
        raise ConfigError(f"{where} MUST be a size, for example 256MiB")
    if isinstance(value, int):
        size = value
    elif isinstance(value, str):
        lowered = value.strip().casefold()
        multiplier = 1
        for suffix, unit in _SIZE_UNITS.items():
            if lowered.endswith(suffix):
                lowered = lowered[: -len(suffix)].strip()
                multiplier = unit
                break
        try:
            size = int(float(lowered) * multiplier)
        except ValueError as exc:
            raise ConfigError(f"{where} MUST be a size, for example 256MiB") from exc
    else:
        raise ConfigError(f"{where} MUST be a size, for example 256MiB")
    if size <= 0:
        raise ConfigError(f"{where} MUST be larger than 0")
    return size


def _mapping(value: Any, where: str, allowed: set[str]) -> dict[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ConfigError(f"{where} MUST be a mapping")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ConfigError(f"{where}: unknown key {unknown[0]!r}")
    return value


def _integer(value: Any, where: str, *, low: int, high: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{where} MUST be an integer")
    if value < low or (high is not None and value > high):
        limit = f"{low}..{high}" if high is not None else f">= {low}"
        raise ConfigError(f"{where} MUST be {limit}")
    return value


def _seconds(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{where} MUST be a number of seconds larger than 0")
    return float(value)


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where} MUST be a non-empty text")
    return value.strip()


def _port(value: Any, where: str) -> int:
    return _integer(value, where, low=1, high=65535)


def _host(raw: Any, index: int) -> HostConfig:
    where = f"hosts[{index}]"
    data = _mapping(raw, where, {"name", "kind", "url", "ssh", "slots", "models", "enabled"})
    name = _text(data.get("name"), f"{where}.name")
    if not _NAME.match(name):
        raise ConfigError(f"{where}.name MUST hold only letters, digits, '.', '_', and '-'")
    where = f"host {name!r}"
    kind = data.get("kind")
    if kind not in HOST_KINDS:
        raise ConfigError(f"{where}: kind MUST be one of {', '.join(HOST_KINDS)}")
    enabled = data.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigError(f"{where}: enabled MUST be true or false")
    slots = _integer(data.get("slots"), f"{where}: slots", low=1)
    models_raw = data.get("models")
    if not isinstance(models_raw, list) or not models_raw:
        raise ConfigError(f"{where}: models MUST be a non-empty list")
    models = tuple(_text(model, f"{where}: models[{i}]") for i, model in enumerate(models_raw))
    if len(set(models)) != len(models):
        raise ConfigError(f"{where}: models MUST NOT repeat a model")
    if ("url" in data) == ("ssh" in data):
        raise ConfigError(f"{where} MUST have either url or ssh")
    ssh = None
    if "ssh" in data:
        ssh_data = _mapping(data["ssh"], f"{where}: ssh", {"target", "local_port", "remote_port"})
        ssh = SshTunnel(
            target=_text(ssh_data.get("target"), f"{where}: ssh.target"),
            local_port=_port(ssh_data.get("local_port"), f"{where}: ssh.local_port"),
            remote_port=_port(ssh_data.get("remote_port", 18090), f"{where}: ssh.remote_port"),
        )
        url = f"http://127.0.0.1:{ssh.local_port}"
    else:
        url = _text(data["url"], f"{where}: url").rstrip("/")
        if not url.startswith(("http://", "https://")):
            raise ConfigError(f"{where}: url MUST start with http:// or https://")
    return HostConfig(name=name, kind=kind, url=url, slots=slots, models=models,
                      enabled=enabled, ssh=ssh)


def parse(raw: Any) -> ProxyConfig:
    """Check the parsed YAML `raw` and return the configuration. Raise ConfigError."""
    data = _mapping(raw, "the configuration",
                    {"listen", "passthrough", "cache", "limits", "health", "hosts"})
    listen = _mapping(data.get("listen"), "listen", {"host", "port"})
    cache = _mapping(data.get("cache"), "cache",
                     {"path", "namespace", "ttl_days", "max_size", "max_response_size"})
    limits = _mapping(data.get("limits"), "limits",
                      {"max_request_size", "queue_limit", "queue_timeout", "upstream_timeout",
                       "attempts"})
    health = _mapping(data.get("health"), "health", {"interval", "timeout"})

    hosts_raw = data.get("hosts")
    if not isinstance(hosts_raw, list) or not hosts_raw:
        raise ConfigError("hosts MUST be a non-empty list")
    hosts = tuple(_host(item, index) for index, item in enumerate(hosts_raw))
    names = [host.name for host in hosts]
    for name in names:
        if names.count(name) > 1:
            raise ConfigError(f"the host name {name!r} is used more than one time")
    local_ports = [host.ssh.local_port for host in hosts if host.ssh is not None]
    for port in local_ports:
        if local_ports.count(port) > 1:
            raise ConfigError(f"the ssh.local_port {port} is used more than one time")

    passthrough = _text(data.get("passthrough"), "passthrough")
    target = next((host for host in hosts if host.name == passthrough), None)
    if target is None or not target.enabled:
        raise ConfigError(f"passthrough MUST name an enabled host, not {passthrough!r}")

    listen_port = _port(listen.get("port", 18092), "listen.port")
    if listen_port in local_ports:
        raise ConfigError(f"listen.port {listen_port} is also an ssh.local_port")
    ttl_days = cache.get("ttl_days", 30)
    return ProxyConfig(
        listen_host=_text(listen.get("host", "127.0.0.1"), "listen.host"),
        listen_port=listen_port,
        passthrough=passthrough,
        hosts=hosts,
        cache_path=Path(_text(cache.get("path", "~/.cache/svoe-vino-model-proxy/cache.sqlite3"),
                              "cache.path")).expanduser(),
        namespace=_text(cache.get("namespace", "svoe-vino-model-proxy-v1"), "cache.namespace"),
        ttl_seconds=int(_seconds(ttl_days, "cache.ttl_days") * 24 * 60 * 60),
        max_cache_bytes=parse_size(cache.get("max_size", "10GiB"), "cache.max_size"),
        max_response_bytes=parse_size(cache.get("max_response_size", "256MiB"),
                                      "cache.max_response_size"),
        max_request_bytes=parse_size(limits.get("max_request_size", "256MiB"),
                                     "limits.max_request_size"),
        queue_limit=_integer(limits.get("queue_limit", 128), "limits.queue_limit", low=1),
        queue_timeout=_seconds(limits.get("queue_timeout", 300), "limits.queue_timeout"),
        upstream_timeout=_seconds(limits.get("upstream_timeout", 300), "limits.upstream_timeout"),
        attempts=_integer(limits.get("attempts", 3), "limits.attempts", low=1),
        health_interval=_seconds(health.get("interval", 10), "health.interval"),
        health_timeout=_seconds(health.get("timeout", 3), "health.timeout"),
    )


def load(path: Path) -> ProxyConfig:
    """Read and check the configuration file `path`. Raise ConfigError."""
    try:
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
    try:
        return parse(raw)
    except ConfigError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
