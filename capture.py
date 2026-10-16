"""Snip: a single-session Windows capture utility.

Tk owns all state and widgets. Tray and hotkey callbacks enqueue actions.
Workers receive a configuration snapshot and return through the same queue.
"""

import ctypes
import io
import logging
import math
import os
import queue
import struct
import threading
import tkinter as tk
import wave
import winsound
from copy import deepcopy
from ctypes import wintypes
from logging.handlers import RotatingFileHandler

import pystray
import win32gui
from PIL import Image, ImageDraw

import active_browser
import clip
import grab
import save
import scroll
import settings
import webpage
from annotate import Annotator
from hotkey import MenuHotkey
from palette import Palette
from region import RegionSelector
from theme import BUSY as COLOR_BUSY
from theme import IDLE as COLOR_IDLE
from theme import TEXT as PAPER
from url_prompt import URLPrompt

log = logging.getLogger("snip")


def _make_soft_beep() -> bytes:
    """A gentle sine-tone confirmation, built once at import.

    Replaces the old winsound.Beep(880, 60) — a PC-speaker square wave, which is
    harsh no matter the volume. A quiet sine at C5 with a 20ms fade in/out reads
    as a soft click instead of a shrill blip, and PlaySound plays it async.
    """
    rate = 44100
    dur = 0.11  # seconds — short, a confirmation not a chime
    freq = 523.25  # C5, lower and rounder than the old 880 Hz
    amp = 0.22  # quiet
    n = int(rate * dur)
    fade = int(rate * 0.02)  # 20ms fade both ends removes the click/edge
    frames = bytearray()
    for i in range(n):
        env = min(i / fade, (n - i) / fade, 1.0)
        sample = amp * env * math.sin(2 * math.pi * freq * i / rate)
        frames += struct.pack("<h", int(sample * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


_SOFT_BEEP = _make_soft_beep()


def _icon_image(color: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 12, 58, 52), radius=10, fill=color)  # camera body
    d.ellipse((22, 22, 42, 42), fill=PAPER)  # lens
    d.ellipse((27, 27, 37, 37), fill=color)
    d.rectangle((24, 6, 40, 14), fill=color)  # viewfinder bump
    return img


class App:
    def __init__(self):
        self.cfg = settings.load()
        self.q = queue.Queue()
        self.state = "idle"
        self.source_hwnd = None
        self.menu_hotkey = None
        self.last_capture = None
        self.root = tk.Tk()
        self.root.withdraw()
        self.icon = pystray.Icon(
            "snip",
            _icon_image(COLOR_IDLE),
            "Snip: ready",
            menu=pystray.Menu(
                pystray.MenuItem("Snip menu", lambda: self.post(self.do_menu), default=True),
                pystray.MenuItem("Open captures folder", lambda: self.post(self.open_folder)),
                pystray.MenuItem("Annotate last capture", lambda: self.post(self.do_annotate)),
                pystray.MenuItem("Capture web address…", lambda: self.post(self.prompt_page)),
                pystray.MenuItem(
                    "Open capture browser", lambda: self.post(self.open_login_browser)
                ),
                pystray.MenuItem("Open config", lambda: self.post(self.open_config)),
                pystray.MenuItem("Reload config", lambda: self.post(self.reload_config)),
                pystray.MenuItem("Quit", lambda: self.post(self.quit)),
            ),
        )

    def post(self, fn):
        self.q.put(fn)

    def poll(self):
        for _ in range(50):
            try:
                fn = self.q.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception as exc:
                self.report_error("Action", exc)
        if self.state != "closing":
            self.root.after(40, self.poll)

    def notify(self, message):
        try:
            self.icon.notify(message, "Snip")
        except Exception:
            pass

    def report_error(self, action, exc):
        # Provider exceptions can contain private URLs. Record type, not contents.
        log.error("%s failed (%s)", action, type(exc).__name__)
        message = (
            str(exc) if isinstance(exc, ValueError) else f"{action} failed ({type(exc).__name__})."
        )
        self.notify(message + " Your existing files were kept.")

    def set_state(self, state):
        self.state = state
        self.icon.icon = _icon_image(COLOR_IDLE if state == "idle" else COLOR_BUSY)
        self.icon.title = f"Snip: {state}"

    def available(self):
        if self.state != "idle":
            self.notify("Finish or close the current Snip action first.")
            return False
        return True

    def beep(self):
        if self.cfg["sounds"]:

            def play():
                try:
                    winsound.PlaySound(_SOFT_BEEP, winsound.SND_MEMORY)
                except RuntimeError:
                    log.warning("Confirmation sound unavailable")

            threading.Thread(target=play, daemon=True).start()

    def saved(self, path, image, cfg):
        self.last_capture = path
        note = ""
        if cfg["copy_to_clipboard"]:
            if image.height > cfg["clipboard_max_height"]:
                note = " · too tall for clipboard, file saved"
            else:
                try:
                    clip.copy_image(image)
                    note = " · on clipboard"
                except Exception:
                    note = " · clipboard unavailable, file saved"
        self.beep()
        self.notify(path.name + note)

    def finish_capture(self, image, kind, cfg=None):
        cfg = cfg or self.cfg
        path = save.save_png(image, kind, cfg["resolved_save_dir"])
        self.saved(path, image, cfg)

    def job(self, name, work, complete=None):
        if not self.available():
            return
        cfg = deepcopy(self.cfg)
        self.set_state(name)

        def worker():
            try:
                result, error = work(cfg), None
            except Exception as exc:
                result, error = None, exc

            def finish():
                self.set_state("idle")
                if error is not None:
                    self.report_error(name, error)
                elif complete:
                    complete(result, cfg)

            self.post(finish)

        threading.Thread(target=worker, name=f"snip-{name}", daemon=False).start()

    def do_menu(self):
        if not self.available():
            return
        self.source_hwnd = win32gui.GetForegroundWindow()
        self.set_state("menu")
        actions = [
            ("s", "Snip a region", self.do_region),
            ("f", "Full screen", self.do_fullscreen),
            ("a", "Active window", self.do_window),
            ("d", "Scrolling capture", self.do_scroll),
            ("u", "Full web page", self.do_fullpage),
            ("e", "Annotate last capture", self.do_annotate),
            ("o", "Open captures folder", self.open_folder),
        ]

        def picked(callback):
            self.set_state("idle")
            if callback:
                self.root.after(230, lambda: self.post(callback))

        try:
            Palette(self.root, actions, picked)
        except Exception:
            self.set_state("idle")
            raise

    def select(self, complete):
        if not self.available():
            return
        self.set_state("selecting")
        try:
            image, origin = grab.virtual_screen(self.cfg["max_pixels"])

            def selected(result):
                self.set_state("idle")
                if result:
                    try:
                        complete(result, origin)
                    except Exception as exc:
                        self.report_error("Capture", exc)

            RegionSelector(self.root, image, origin, selected)
        except Exception:
            self.set_state("idle")
            raise

    def do_region(self):
        self.select(lambda result, origin: self.finish_capture(result[0], "snip"))

    def do_fullscreen(self):
        if self.available():
            image, _ = grab.virtual_screen(self.cfg["max_pixels"])
            self.finish_capture(image, "screen")

    def do_window(self):
        if not self.available():
            return
        hwnd = self.source_hwnd or win32gui.GetForegroundWindow()
        self.source_hwnd = None
        if not win32gui.IsWindow(hwnd):
            self.notify("The selected window has closed.")
            return
        # A screenshot is visible pixels, not hidden or minimized window contents.
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            self.notify("Select the window again and retry.")
            return
        self.set_state("window")

        def capture_window():
            try:
                if win32gui.GetForegroundWindow() != hwnd:
                    raise ValueError("The selected window is no longer in front; retry.")
                image = grab.grab_window(hwnd, self.cfg["max_pixels"])
                if image is None:
                    raise ValueError("The selected window has no visible capture area.")
                self.finish_capture(image, "window")
            finally:
                self.set_state("idle")

        self.root.after(150, lambda: self.post(capture_window))

    def do_scroll(self):
        target = self.source_hwnd or win32gui.GetForegroundWindow()
        self.source_hwnd = None

        def selected(result, origin):
            _, box = result
            bbox = (box[0] + origin[0], box[1] + origin[1], box[2] + origin[0], box[3] + origin[1])
            try:
                win32gui.SetForegroundWindow(target)
            except Exception:
                self.notify("Select the scrollable window again and retry.")
                return
            self.notify("Scrolling capture: Esc or move the pointer to stop.")

            def complete(image, cfg):
                if image is None:
                    self.notify("Select an area at least 40 pixels wide and 240 pixels tall.")
                else:
                    self.finish_capture(image, "scroll", cfg)

            self.job("scrolling", lambda cfg: scroll.capture_scrolling(bbox, cfg), complete)

        self.select(selected)

    def do_fullpage(self):
        hwnd = self.source_hwnd or active_browser.foreground_browser()
        self.source_hwnd = None

        def ready(url, _cfg):
            if url:
                self.capture_url(url)
            else:
                self.prompt_page()

        self.job("reading address", lambda cfg: active_browser.read_url(hwnd), ready)

    def prompt_page(self):
        if not self.available():
            return
        self.set_state("web address")
        try:
            url = URLPrompt(self.root).show()
        finally:
            self.set_state("idle")
        if url:
            self.capture_url(url)

    def capture_url(self, url):
        def work(cfg):
            target = save.next_path("page", cfg["resolved_save_dir"])
            return webpage.capture_page(url, target, cfg)

        def complete(path, cfg):
            with Image.open(path) as image:
                self.saved(path, image, cfg)

        self.job("web capture", work, complete)

    def do_annotate(self):
        if not self.available():
            return
        path = self.last_capture
        if path is None or not path.exists():
            path = max(
                self.cfg["resolved_save_dir"].glob("*.png"),
                key=lambda p: p.stat().st_mtime,
                default=None,
            )
        if path is None:
            self.notify("No captures yet. Make a capture first.")
            return
        self.set_state("annotating")
        try:
            Annotator(
                self.root,
                path,
                self.notify,
                on_close=lambda: self.set_state("idle"),
                cfg=deepcopy(self.cfg),
            )
        except Exception:
            self.set_state("idle")
            raise

    def open_login_browser(self):
        self.job(
            "capture browser",
            webpage.open_login_browser,
            lambda result, cfg: self.notify("Capture browser closed. Local sessions retained."),
        )

    def open_folder(self):
        folder = self.cfg["resolved_save_dir"]
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def open_config(self):
        local = settings.APP_DIR / "config.local.toml"
        if not local.exists():
            local.write_text("# Override config.toml defaults here.\n", encoding="utf-8")
        os.startfile(local)

    def reload_config(self):
        if self.available():
            self.cfg = settings.load()
            self.notify("Configuration reloaded.")

    def quit(self):
        if not self.available():
            return
        self.set_state("closing")
        self.root.quit()

    def run(self, register_hotkey=True):
        self.icon.run_detached()
        self.poll()
        try:
            if register_hotkey:
                try:
                    self.menu_hotkey = MenuHotkey(lambda: self.post(self.do_menu))
                except RuntimeError as exc:
                    self.notify(str(exc))
            log.info("started")
            self.root.mainloop()
        finally:
            if self.menu_hotkey:
                self.menu_hotkey.close()
            self.icon.stop()
            self.root.destroy()
            log.info("stopped")


class InstanceGuard:
    """Keep the legacy name so installed and public editions cannot compete."""

    def __init__(self):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        self.kernel = kernel
        self.handle = kernel.CreateMutexW(None, False, "SwayRise.Capture.SingleInstance")
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.already_running = ctypes.get_last_error() == 183

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except OSError:
        pass
    handler = RotatingFileHandler(
        settings.APP_DIR / "capture.log", maxBytes=1000000, backupCount=2, encoding="utf-8"
    )
    logging.basicConfig(
        handlers=[handler], level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    guard = InstanceGuard()
    try:
        if guard.already_running:
            ctypes.windll.user32.MessageBoxW(
                None, "Snip is already running. Use its tray icon.", "Snip", 0x40
            )
            return
        App().run()
    except Exception as exc:
        log.error("Startup failed (%s)", type(exc).__name__)
        ctypes.windll.user32.MessageBoxW(
            None, "Snip could not start. Check config.local.toml and capture.log.", "Snip", 0x10
        )
        raise
    finally:
        guard.close()


if __name__ == "__main__":
    main()
