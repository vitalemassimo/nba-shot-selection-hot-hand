"""Load config.yaml and expose project paths."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
FIGURES = ROOT / "reports" / "figures"


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    """Return the project configuration as a dict."""
    with open(path) as f:
        return yaml.safe_load(f)
