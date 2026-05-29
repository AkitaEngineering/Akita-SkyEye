import json
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_config_path(filepath):
    config_path = Path(filepath)
    if not config_path.is_absolute():
        config_path = _PROJECT_ROOT / config_path
    return config_path


def _load_config(filepath):
    with _resolve_config_path(filepath).open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def load_drone_config(filepath="config/drone_config.json"):
    return _load_config(filepath)


def load_reticulum_config(filepath="config/reticulum_config.json"):
    return _load_config(filepath)
