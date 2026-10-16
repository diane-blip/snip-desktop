"""Dated-filename PNG saving."""
import re
from datetime import datetime
from pathlib import Path

from PIL import Image


def _slug(text: str) -> str:
    text = re.sub(r"^https?://", "", text).strip("/")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text[:60] or "page"


def next_path(kind: str, save_dir: Path, label: str | None = None) -> Path:
    """Return an unused dated PNG path without writing a placeholder file."""
    save_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base = f"{stamp}_{kind}" + (f"_{_slug(label)}" if label else "")
    path = save_dir / f"{base}.png"
    n = 2
    while path.exists():
        path = save_dir / f"{base}-{n}.png"
        n += 1
    return path


def save_png(img: Image.Image, kind: str, save_dir: Path, label: str | None = None) -> Path:
    path = next_path(kind, save_dir, label)
    img.save(path, "PNG")
    return path
