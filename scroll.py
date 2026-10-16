"""Scrolling capture: pick a region, the app scrolls it and stitches the frames
into one tall image — GoFullPage for anything (PDFs, Obsidian, Slack, ...).

How it works: grab a frame, send mouse-wheel scrolls at the region's center,
grab again, find how far the content moved by matching the previous frame's
bottom band inside the new frame, and append only the new rows. Stops at the
bottom (content stops moving), on Esc, or at the configured height cap.
"""
import ctypes
import ctypes.wintypes as wintypes
import time

import keyboard
import mss
import numpy as np
from PIL import Image

BAND = 120        # rows from the previous frame's bottom used for matching
COL_STEP = 8      # sample every Nth column for the match signature
MATCH_MAX_ERR = 12.0  # mean gray-level error above this = unreliable match


def _sig(arr: np.ndarray) -> np.ndarray:
    """Grayscale, column-subsampled signature for fast row matching."""
    return arr.mean(axis=2)[:, ::COL_STEP].astype(np.int16)


def find_offset(prev_sig: np.ndarray, next_sig: np.ndarray) -> tuple[int, float]:
    """How many pixels the content moved up between frames (0 = none).

    The previous frame's bottom band should reappear higher up in the new
    frame; the shift is the scroll distance.
    """
    h = prev_sig.shape[0]
    band = prev_sig[h - BAND:]
    best_dy, best_err = 0, float("inf")
    for dy in range(0, h - BAND):
        win = next_sig[h - BAND - dy: h - dy]
        err = float(np.abs(win - band).mean())
        if err < best_err:
            best_dy, best_err = dy, err
    return best_dy, best_err


def stitch(frames_new_rows: list[np.ndarray]) -> Image.Image:
    return Image.fromarray(np.vstack(frames_new_rows))


def capture_scrolling(bbox: tuple[int, int, int, int], cfg: dict, status=None) -> Image.Image | None:
    """bbox = (left, top, right, bottom) in screen coordinates."""
    sc = cfg.get("scroll", {})
    settle_s = sc.get("settle_ms", 450) / 1000
    ticks = sc.get("wheel_ticks", 4)
    max_height = sc.get("max_height", 20000)
    max_steps = sc.get("max_steps", 80)

    left, top, right, bottom = bbox
    w, h = right - left, bottom - top
    if w < 40 or h < BAND * 2:
        return None
    region = {"left": left, "top": top, "width": w, "height": h}

    user32 = ctypes.windll.user32
    orig = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(orig))
    cx, cy = left + w // 2, top + h // 2

    def grab(sct) -> np.ndarray:
        shot = sct.grab(region)
        return np.array(Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX"))

    pieces: list[np.ndarray] = []
    total = 0
    stalls = 0
    try:
        with mss.mss() as sct:
            user32.SetCursorPos(cx, cy)
            time.sleep(0.15)
            prev = grab(sct)
            pieces.append(prev)
            total = prev.shape[0]
            prev_sig = _sig(prev)

            for step in range(max_steps):
                if keyboard.is_pressed("esc"):
                    break
                user32.SetCursorPos(cx, cy)
                user32.mouse_event(0x0800, 0, 0, -120 * ticks, 0)  # wheel down
                time.sleep(settle_s)

                nxt = grab(sct)
                if np.array_equal(nxt, prev):
                    stalls += 1
                    if stalls >= 2:
                        break  # bottom reached
                    continue
                nxt_sig = _sig(nxt)
                dy, err = find_offset(prev_sig, nxt_sig)
                if dy <= 0 or err > MATCH_MAX_ERR:
                    stalls += 1
                    if stalls >= 2:
                        break  # can't match (animation/blank area) or no movement
                    prev, prev_sig = nxt, nxt_sig
                    continue
                stalls = 0
                pieces.append(nxt[h - dy:])
                total += dy
                if status:
                    status(total)
                prev, prev_sig = nxt, nxt_sig
                if total >= max_height:
                    break
    finally:
        user32.SetCursorPos(orig.x, orig.y)

    if not pieces:
        return None
    return stitch(pieces)
