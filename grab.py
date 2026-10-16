"""Screen grabs via mss. All coordinates are physical pixels (the app sets
per-monitor DPI awareness at startup, so Windows reports real pixels)."""

import ctypes
from ctypes import wintypes

import mss
from PIL import Image


def virtual_screen(max_pixels=40000000) -> tuple[Image.Image, tuple[int, int]]:
    """Grab the entire virtual desktop (all monitors).

    Returns (image, (left, top)) where left/top is the virtual-screen origin
    in screen coordinates (negative when a monitor sits left of/above primary).
    """
    with mss.MSS() as sct:
        mon = sct.monitors[0]
        if mon["width"] * mon["height"] > max_pixels:
            raise ValueError("Desktop exceeds the configured capture size limit")
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        return img, (mon["left"], mon["top"])


def foreground_window_bbox(hwnd=None) -> tuple[int, int, int, int] | None:
    """Screen-coordinate bounds of the foreground window, without the drop
    shadow (DWM extended frame bounds; falls back to GetWindowRect)."""
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.IsWindow.argtypes = (wintypes.HWND,)
    user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    hwnd = hwnd or user32.GetForegroundWindow()
    if not hwnd or not user32.IsWindow(hwnd):
        return None
    rect = wintypes.RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    try:
        ctypes.windll.dwmapi.DwmGetWindowAttribute.argtypes = (
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
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


def grab_window(hwnd=None, max_pixels=40000000) -> Image.Image | None:
    bbox = foreground_window_bbox(hwnd)
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    with mss.MSS() as sct:
        desktop = sct.monitors[0]
        left, top = max(x0, desktop["left"]), max(y0, desktop["top"])
        right = min(x1, desktop["left"] + desktop["width"])
        bottom = min(y1, desktop["top"] + desktop["height"])
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None
        if width * height > max_pixels:
            raise ValueError("Window exceeds the configured capture size limit")
        shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
