"""Give each subprocess test its own YAML file and archive directory."""

import atexit
import os
from pathlib import Path
import shutil
import tempfile

import yaml


def process_environment(template, *, output_dir=None, sam3_endpoint=None, limits=None):
    document = yaml.safe_load(Path(template).read_text(encoding="utf-8"))
    settings = document["matcher"]
    if output_dir is not None:
        settings["output_dir"] = str(output_dir)
    if sam3_endpoint is not None:
        settings["sam3_endpoint"] = sam3_endpoint
    if limits is not None:
        settings["limits"] = limits
    directory = Path(tempfile.mkdtemp(prefix="matcher-test-config-"))
    atexit.register(shutil.rmtree, directory, ignore_errors=True)
    path = directory / "config.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    environment = dict(os.environ, SVOE_VINO_MATCHER_CONFIG=str(path))
    environment.pop("SAM3_ENDPOINT", None)
    return environment
