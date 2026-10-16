"""Screen grabs via mss. All coordinates are physical pixels (the app sets
per-monitor DPI awareness at startup, so Windows reports real pixels)."""
import ctypes
from ctypes import wintypes

import mss
from PIL import Image


def virtual_screen() -> tuple[Image.Image, tuple[int, int]]:
    """Grab the entire virtual desktop (all monitors).

    Returns (image, (left, top)) where left/top is the virtual-screen origin
    in screen coordinates (negative when a monitor sits left of/above primary).
    """
    with mss.mss() as sct:
        mon = sct.monitors[0]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        return img, (mon["left"], mon["top"])


def foreground_window_bbox() -> tuple[int, int, int, int] | None:
    """Screen-coordinate bounds of the foreground window, without the drop
    shadow (DWM extended frame bounds; falls back to GetWindowRect)."""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    rect = wintypes.RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    try:
        res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
        )
        if res != 0:
            raise OSError(res)
    except Exception:
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def grab_window() -> Image.Image | None:
    bbox = foreground_window_bbox()
    if not bbox:
        return None
    img, (left, top) = virtual_screen()
    l, t, r, b = bbox
    crop = (
        max(l - left, 0),
        max(t - top, 0),
        min(r - left, img.width),
        min(b - top, img.height),
    )
    if crop[2] <= crop[0] or crop[3] <= crop[1]:
        return None
    return img.crop(crop)
