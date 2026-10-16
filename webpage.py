"""Full-page web capture via Playwright Chromium.

A persistent profile (browser-profile/, gitignored) keeps logins between runs:
log in once via open_login_browser(), then headless captures of that site see
the logged-in page. Playwright is imported lazily so the tray app starts fast.
"""
from pathlib import Path


def capture_page(url: str, out_path: Path, cfg: dict) -> Path:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    fp = cfg.get("fullpage", {})
    width = fp.get("viewport_width", 1440)
    timeout_ms = int(fp.get("timeout_seconds", 60) * 1000)
    settle_ms = fp.get("settle_ms", 1500)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(cfg["resolved_profile_dir"]),
            headless=True,
            viewport={"width": width, "height": 900},
        )
        try:
            page = ctx.new_page()
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            except PWTimeout:
                response = None  # capture what rendered when a slow request never settles
            if response is not None and response.status >= 400:
                raise RuntimeError(f"Page returned HTTP {response.status}")

            # Trigger images and sections that load only as they approach the viewport.
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(200)
            previous_height = 0
            for _ in range(120):
                height = page.evaluate(
                    "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
                )
                y = page.evaluate("window.scrollY + window.innerHeight")
                if y >= height and height == previous_height:
                    break
                previous_height = height
                page.evaluate("window.scrollBy(0, Math.max(500, window.innerHeight * 0.8))")
                page.wait_for_timeout(120)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(settle_ms)
            page.screenshot(path=str(out_path), full_page=True)
        finally:
            ctx.close()
    return out_path


def open_login_browser(cfg: dict, url: str | None = None) -> None:
    """Open a visible browser on the SAME profile so Diane can log into sites.
    Blocks until she closes the window; sessions persist for later captures."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(cfg["resolved_profile_dir"]),
            headless=False,
            viewport=None,
            no_viewport=True,
            args=["--start-maximized"],
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(url or "about:blank")
            page.wait_for_event("close", timeout=0)  # until she closes the window
        except Exception:
            pass  # window closed / context gone — that's the normal exit
        finally:
            try:
                ctx.close()
            except Exception:
                pass
