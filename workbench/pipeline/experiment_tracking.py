"""Use the shared optional matcher experiment exporter from Workbench scripts."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from matcher.mlflow_tracking import export_run  # noqa: E402


def export_benchmark(directory, log):
    return export_run(directory, "workbench", log=log)
