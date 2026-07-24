"""Load configuration and resolve project-relative paths."""
from pathlib import Path
import yaml

# Project root = the folder that contains this src/ package.
ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None) -> dict:
    """Read config.yaml (or a custom path) into a plain dict."""
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def project_path(rel) -> Path:
    """Turn a config path like 'state/x.json' into an absolute path under ROOT."""
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p
