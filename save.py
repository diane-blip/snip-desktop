"""Unique PNG names and atomic publication; URLs never enter filenames."""

import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image


def next_path(kind: str, save_dir: Path) -> Path:
    if kind not in {"snip", "screen", "window", "scroll", "page", "annotated"}:
        raise ValueError("Unknown capture kind")
    save_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return save_dir / f"{stamp}_{kind}_{uuid.uuid4().hex[:12]}.png"


def write_png(img: Image.Image, target: Path) -> Path:
    """Publish only a complete image. Windows rename refuses existing files."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".snip-", suffix=".tmp", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as output:
            img.save(output, "PNG")
            output.flush()
            os.fsync(output.fileno())
        temporary.rename(target)
        return target
    finally:
        temporary.unlink(missing_ok=True)


def save_png(img: Image.Image, kind: str, save_dir: Path) -> Path:
    return write_png(img, next_path(kind, save_dir))
