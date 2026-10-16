"""Read the URL from the browser window that launched a capture.

The global hotkey leaves the browser focused. The pop-up palette briefly takes
focus, so Capture remembers the browser HWND before showing it and restores
that window before copying its address bar.
"""
import re
import time

import keyboard
import pyperclip
import win32gui


URL_RE = re.compile(r"^https?://\S+$", re.I)
BROWSER_CLASSES = {
    "Chrome_WidgetWin_1",  # Chrome, Edge, Brave and other Chromium browsers
    "MozillaWindowClass",  # Firefox
}


def foreground_browser() -> int | None:
    """Return the active browser HWND, or None when another app is active."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd or win32gui.GetClassName(hwnd) not in BROWSER_CLASSES:
        return None
    return hwnd


def read_url(hwnd: int | None) -> str | None:
    """Copy and return ``hwnd``'s address bar without requiring user setup."""
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    if win32gui.GetClassName(hwnd) not in BROWSER_CLASSES:
        return None

    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.12)
        pyperclip.copy("")
        keyboard.send("ctrl+l")
        time.sleep(0.08)
        keyboard.send("ctrl+c")
        time.sleep(0.12)
        text = (pyperclip.paste() or "").strip()
    except Exception:
        return None
    finally:
        try:
            keyboard.send("esc")
        except Exception:
            pass

    return text if URL_RE.match(text) else None
