"""Select an independent SigLIP2 pipeline for segmented shelf bottles."""

from pathlib import Path

import yaml

from .service import (ConfigError, GROUP_MIN_FULL_SCORE, Siglip2Matcher,
                      _load_siglip2, _endpoint)


class SegmentedSiglip2Matcher(Siglip2Matcher):
    """Rank the masked bottle against `full`, as the lab `*-seg` pipeline does."""

    @property
    def can_match_group(self) -> bool:
        return True  # The SigLIP2 loader already requires the view `full`.

    def match_group_many(self, images, labels, k):
        if len(images) != len(labels):
            raise ValueError("group image and label counts differ")
        # Labels select usable segments. They do not rank wine variants in this mode.
        return [[pair for pair in ranked if pair[1] >= GROUP_MIN_FULL_SCORE]
                for ranked in self.match_many(images, k)]


def load_group_matcher(config_path, fallback):
    """Keep the existing group matcher unless `matcher.group_pipeline` is set."""
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    settings = config["matcher"]
    if "group_pipeline" not in settings:
        return fallback
    name = settings["group_pipeline"]
    if not isinstance(name, str) or not name:
        raise ConfigError("matcher.group_pipeline MUST name one pipeline")
    entry = next((entry for entry in config["pipeline"] if entry["name"] == name), None)
    if entry is None:
        raise ConfigError("matcher.group_pipeline names an unknown pipeline: %s" % name)
    if entry.get("backend") != "siglip2":
        raise ConfigError("matcher.group_pipeline requires backend siglip2")
    loaded = _load_siglip2(name, entry, fallback.output_dir, fallback.token)
    if "quality_model" in entry:
        model = entry["quality_model"]
        if not isinstance(model, str) or not model.strip():
            raise ConfigError("pipeline %s quality_model MUST be a nonempty name" % name)
        from .group_quality_runtime import QualityGroupMatcher
        endpoint = _endpoint(entry.get("quality_endpoint", entry.get("endpoint")),
                             name, "quality_endpoint")
        return QualityGroupMatcher(pipeline=name, backend=loaded.backend,
                                   output_dir=loaded.output_dir, token=loaded.token,
                                   quality_endpoint=endpoint, quality_model=model)
    return SegmentedSiglip2Matcher(pipeline=name, backend=loaded.backend,
                                  output_dir=loaded.output_dir, token=loaded.token)
