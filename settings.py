"""Validated defaults with installation-local overrides."""

import tomllib
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def _merge(base, overrides):
    for key, value in overrides.items():
        if key not in base:
            raise ValueError(f"Unknown setting: {key}")
        if isinstance(base[key], dict):
            if not isinstance(value, dict):
                raise ValueError(f"{key} must be a table")
            _merge(base[key], value)
        else:
            base[key] = value


def _integer(table, key, low, high):
    if type(table[key]) is not int or not low <= table[key] <= high:
        raise ValueError(f"{key} must be an integer from {low} to {high}")


def load():
    with (APP_DIR / "config.toml").open("rb") as source:
        cfg = tomllib.load(source)
    local = APP_DIR / "config.local.toml"
    if local.exists():
        with local.open("rb") as source:
            _merge(cfg, tomllib.load(source))
    if not isinstance(cfg["save_dir"], str) or not cfg["save_dir"].strip():
        raise ValueError("save_dir must be a nonempty path")
    for key in ("sounds", "copy_to_clipboard"):
        if type(cfg[key]) is not bool:
            raise ValueError(f"{key} must be true or false")
    _integer(cfg, "clipboard_max_height", 100, 20000)
    _integer(cfg, "max_pixels", 1000000, 80000000)
    for key, low, high in (
        ("wheel_ticks", 1, 10),
        ("settle_ms", 100, 3000),
        ("max_height", 500, 30000),
        ("max_steps", 1, 120),
    ):
        _integer(cfg["scroll"], key, low, high)
    for key, low, high in (
        ("viewport_width", 320, 3840),
        ("timeout_seconds", 5, 120),
        ("settle_ms", 0, 5000),
        ("max_height", 900, 30000),
    ):
        _integer(cfg["fullpage"], key, low, high)
    path = Path(cfg["save_dir"]).expanduser()
    cfg["resolved_save_dir"] = path if path.is_absolute() else APP_DIR / path
    cfg["resolved_profile_dir"] = APP_DIR / "browser-profile"
    return cfg
