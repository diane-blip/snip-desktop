"""Config loading. Everything resolves relative to the app folder."""
import tomllib
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def load() -> dict:
    with open(APP_DIR / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    cfg["resolved_save_dir"] = Path(cfg["save_dir"]).expanduser()
    cfg["resolved_profile_dir"] = APP_DIR / "browser-profile"
    return cfg
