"""Load configuration and resolve project-relative paths."""
from collections.abc import Mapping
from pathlib import Path
import yaml

# Project root = the folder that contains this src/ package.
ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None) -> dict:
    """Read config.yaml (or a custom path) into a plain dict."""
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _deep_update(target, updates: Mapping) -> None:
    """Recursively overlay `updates` onto a mapping in place (preserves other keys)."""
    for k, v in updates.items():
        if isinstance(v, Mapping) and isinstance(target.get(k), Mapping):
            _deep_update(target[k], v)
        else:
            target[k] = v


def save_config(updates: dict, path=None) -> None:
    """Write `updates` back into config.yaml, preserving comments and key order.

    Reloads the file with a round-trip parser and overlays only the keys present
    in `updates`, so all explanatory comments and formatting survive. Requires
    ruamel.yaml (see requirements.txt).
    """
    from ruamel.yaml import YAML

    cfg_path = Path(path) if path else ROOT / "config.yaml"
    yaml_rt = YAML()
    yaml_rt.preserve_quotes = True
    with open(cfg_path, "r", encoding="utf-8") as f:
        doc = yaml_rt.load(f)

    _deep_update(doc, updates)

    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml_rt.dump(doc, f)


def project_path(rel) -> Path:
    """Turn a config path like 'state/x.json' into an absolute path under ROOT."""
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p
