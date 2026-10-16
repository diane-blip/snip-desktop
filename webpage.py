"""Bounded full-page capture in a separate, installation-local browser profile."""

import io
import os
import time
from pathlib import Path

from PIL import Image

from active_browser import normalize_url
from save import write_png

# Keep this installation's Chromium inside its virtual environment.
# No shared browser profile or machine-wide browser installation is changed.
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"


def capture_page(url: str, out_path: Path, cfg: dict) -> Path:
    from playwright.sync_api import sync_playwright

    url = normalize_url(url)
    if not url:
        raise ValueError("Use a complete http:// or https:// URL without embedded credentials.")
    fp = cfg["fullpage"]
    width = fp["viewport_width"]
    timeout_ms = fp["timeout_seconds"] * 1000
    max_height = min(fp.get("max_height", 20000), cfg.get("max_pixels", 40000000) // width)
    deadline = time.monotonic() + fp["timeout_seconds"]
    with sync_playwright() as driver:
        ctx = driver.chromium.launch_persistent_context(
            str(cfg["resolved_profile_dir"]),
            headless=True,
            viewport={"width": width, "height": 900},
            timeout=timeout_ms,
            accept_downloads=False,
        )
        try:
            page = ctx.new_page()
            page.set_default_timeout(timeout_ms)
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if response is None or response.status >= 400:
                raise RuntimeError("The page did not return a successful document.")
            dimensions = """() => ({width: Math.max(document.documentElement.scrollWidth,
                document.body?.scrollWidth || 0), height: Math.max(document.documentElement.scrollHeight,
                document.body?.scrollHeight || 0)})"""
            for _ in range(120):
                size = page.evaluate(dimensions)
                if size["height"] > max_height or size["width"] * size["height"] > cfg.get(
                    "max_pixels", 40000000
                ):
                    raise ValueError("Page exceeds the capture size limit; use a region capture.")
                if time.monotonic() >= deadline:
                    raise TimeoutError("Page capture exceeded its time limit.")
                before = page.evaluate("window.scrollY")
                page.evaluate("window.scrollBy(0, Math.max(400, window.innerHeight * 0.7))")
                page.wait_for_timeout(120)
                if page.evaluate("window.scrollY") == before:
                    break
            else:
                raise ValueError("Page continues growing; use a region capture.")
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(fp["settle_ms"])
            size = page.evaluate(dimensions)
            if size["height"] > max_height or size["width"] * size["height"] > cfg.get(
                "max_pixels", 40000000
            ):
                raise ValueError("Page exceeds the capture size limit.")
            remaining = int((deadline - time.monotonic()) * 1000)
            if remaining <= 0:
                raise TimeoutError("Page capture exceeded its time limit.")
            data = page.screenshot(full_page=True, animations="disabled", timeout=remaining)
            with Image.open(io.BytesIO(data)) as image:
                return write_png(image, out_path)
        finally:
            ctx.close()


def open_login_browser(cfg: dict):
    """Visible separate profile; block until every page is closed."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        ctx = driver.chromium.launch_persistent_context(
            str(cfg["resolved_profile_dir"]),
            headless=False,
            no_viewport=True,
            args=["--start-maximized"],
            accept_downloads=False,
        )
        try:
            while ctx.pages:
                page = ctx.pages[0]
                try:
                    page.wait_for_event("close", timeout=0)
                except Exception:
                    if ctx.pages:
                        raise
        finally:
            ctx.close()
