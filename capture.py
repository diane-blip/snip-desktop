"""Snip — screen capture for Diane.

  Ctrl+Shift+S  the capture menu — every action one letter away:
                   S snip · F full screen · A window · D scrolling
                   U full web page · E annotate last · O open folder
  Only Ctrl+Shift+S is registered globally; the tray icon also opens the menu.

Every capture: PNG in the captures folder + copied to the clipboard + a toast.

Threading: Tk owns the main thread (the region overlay and URL prompt need it);
pystray runs detached; tray clicks post work onto the Tk
thread through a queue. Slow work (full-page browser captures) runs in worker
threads so the tray stays responsive.
"""
import ctypes
from ctypes import wintypes
import io
import logging
import math
import queue
import re
import struct
import threading
import wave
import winsound

import pystray
import tkinter as tk
from PIL import Image, ImageDraw

import clip
import active_browser
import grab
import save
import scroll
import settings
import webpage
from annotate import Annotator
from palette import Palette
from region import RegionSelector

COLOR_IDLE = "#8a8a8a"
COLOR_BUSY = "#AD8326"
PINK = "#F0BDCE"  # softened from brand #F49CBB (lighter, desaturated) at Di's request
INK = "#111111"
PAPER = "#FEFCFD"
URL_RE = re.compile(r"^(https?://|www\.)\S+$", re.I)


def _make_soft_beep() -> bytes:
    """A gentle sine-tone confirmation, built once at import.

    Replaces the old winsound.Beep(880, 60) — a PC-speaker square wave, which is
    harsh no matter the volume. A quiet sine at C5 with a 20ms fade in/out reads
    as a soft click instead of a shrill blip, and PlaySound plays it async.
    """
    rate = 44100
    dur = 0.11          # seconds — short, a confirmation not a chime
    freq = 523.25       # C5, lower and rounder than the old 880 Hz
    amp = 0.22          # quiet
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

# The app runs headless under pythonw, so errors are invisible without this.
logging.basicConfig(
    filename=settings.APP_DIR / "capture.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("capture")


class MenuHotkey:
    """One Windows-owned menu shortcut; no blocking keyboard hook."""
    identifier = 0x534E
    modifiers = 0x0002 | 0x0004 | 0x4000  # Ctrl, Shift, no auto-repeat.
    key = 0x53

    def __init__(self, callback):
        self.callback = callback
        self.ready = threading.Event()
        self.stopping = threading.Event()
        self.registered = False
        self.error = None
        self.thread_id = None
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        self.user32.GetMessageW.restype = ctypes.c_int
        self.user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
        self.user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        if not self.ready.wait(2):
            self.close()
            raise RuntimeError("Snip shortcut startup timed out.")
        if self.error:
            self.close()
            raise RuntimeError(self.error)

    def run(self):
        self.thread_id = self.kernel32.GetCurrentThreadId()
        message = wintypes.MSG()
        self.user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        try:
            if not self.user32.RegisterHotKey(None, self.identifier, self.modifiers, self.key):
                self.error = f"Ctrl+Shift+S unavailable (Windows {ctypes.get_last_error()}). Use the Snip tray icon."
                return
            self.registered = True
            self.ready.set()
            while not self.stopping.is_set():
                result = self.user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result <= 0:
                    break
                if message.message == 0x0312 and message.wParam == self.identifier:
                    self.callback()  # Queue only; capture work runs on Tk's thread.
        finally:
            if self.registered:
                self.user32.UnregisterHotKey(None, self.identifier)
            self.registered = False
            self.ready.set()

    def close(self):
        self.stopping.set()
        self.ready.wait(2)
        if self.thread.is_alive() and self.thread_id:
            self.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
        self.thread.join(2)
        if self.thread.is_alive():
            raise RuntimeError("Snip shortcut thread did not stop.")

# Physical pixels everywhere (overlay coordinates must match mss grabs).
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


def _icon_image(color: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 12, 58, 52), radius=10, fill=color)      # camera body
    d.ellipse((22, 22, 42, 42), fill=PAPER)                          # lens
    d.ellipse((27, 27, 37, 37), fill=color)
    d.rectangle((24, 6, 40, 14), fill=color)                         # viewfinder bump
    return img


class App:
    def __init__(self):
        self.cfg = settings.load()
        self.q: queue.Queue = queue.Queue()
        self.page_busy = False
        self.selector_open = False
        self.scroll_busy = False
        self.annotator_open = False
        self.palette_open = False
        self.fullpage_source_hwnd = None
        self.menu_hotkey = None

        self.root = tk.Tk()
        self.root.withdraw()

        self.icon = pystray.Icon(
            "capture", _icon_image(COLOR_IDLE),
            "Snip · Ctrl+Shift+S or click for the menu",
            menu=pystray.Menu(
                pystray.MenuItem("Snip menu", lambda: self.post(self.do_menu), default=True),
                pystray.MenuItem("Open captures folder", self.open_folder),
                pystray.MenuItem("Annotate last capture", lambda: self.post(self.do_annotate)),
                pystray.MenuItem("Snip full page…", lambda: self.post(lambda: self.do_fullpage(force_prompt=True))),
                pystray.MenuItem("Open capture browser (log in to sites)", self.open_login_browser),
                pystray.MenuItem("Open config", self.open_config),
                pystray.MenuItem("Reload config", self.reload_config),
                pystray.MenuItem("Quit", self.quit),
            ),
        )

    # -- plumbing --------------------------------------------------------------

    def post(self, fn) -> None:
        """Run fn on the Tk main thread."""
        self.q.put(fn)

    def poll(self) -> None:
        # A raised exception here would end the after() chain and silently kill
        # every hotkey, so each queued action is contained.
        try:
            while True:
                fn = self.q.get_nowait()
                try:
                    fn()
                except Exception as e:
                    log.exception("queued action failed")
                    self.selector_open = False
                    self.notify(f"Snip error: {e}")
        except queue.Empty:
            pass
        self.root.after(40, self.poll)

    def notify(self, message: str) -> None:
        try:
            self.icon.notify(message, "Snip")
        except Exception:
            pass

    def beep(self) -> None:
        if self.cfg.get("sounds", True):
            # winsound rejects SND_MEMORY + SND_ASYNC. Synchronous playback in
            # a tiny daemon thread stays non-blocking and can never break save.
            def play():
                try:
                    winsound.PlaySound(_SOFT_BEEP, winsound.SND_MEMORY)
                except Exception as exc:
                    log.warning("confirmation sound failed: %s", exc)
            threading.Thread(target=play, daemon=True).start()

    def set_busy(self, busy: bool) -> None:
        self.icon.icon = _icon_image(COLOR_BUSY if busy else COLOR_IDLE)

    def finish_capture(self, img: Image.Image, kind: str, label: str | None = None) -> None:
        path = save.save_png(img, kind, self.cfg["resolved_save_dir"], label)
        clip_note = ""
        if self.cfg.get("copy_to_clipboard", True):
            if img.height <= self.cfg.get("clipboard_max_height", 8000):
                try:
                    clip.copy_image(img)
                    clip_note = " · on clipboard"
                except Exception:
                    clip_note = " · clipboard busy, file saved"
            else:
                clip_note = " · too tall for clipboard, file saved"
        self.beep()
        self.notify(f"{path.name}{clip_note}")

    # -- capture modes (run on the Tk thread) -----------------------------------

    def do_menu(self) -> None:
        """The pop-up palette: one hotkey, every capture one letter away."""
        if self.palette_open:
            return
        self.palette_open = True
        self.fullpage_source_hwnd = active_browser.foreground_browser()
        actions = [
            ("s", "Snip a region", self.do_region),
            ("f", "Full screen", self.do_fullscreen),
            ("a", "Active window", self.do_window),
            ("d", "Scrolling capture", self.do_scroll),
            ("u", "Full web page", self.do_fullpage),
            ("e", "Annotate last capture", self.do_annotate),
            ("o", "Open captures folder", self.open_folder),
        ]

        def picked(cb):
            self.palette_open = False
            if cb is not None:
                log.info("palette pick: %s", cb.__name__)
                # Let the palette vanish before any screen grab or focus check,
                # so it can't appear in the shot or steal the "active window".
                self.root.after(230, cb)

        Palette(self.root, actions, picked)

    def do_region(self) -> None:
        if self.selector_open:
            return
        self.selector_open = True
        img, origin = grab.virtual_screen()

        def done(result):
            self.selector_open = False
            if result is not None:
                cropped, _box = result
                self.finish_capture(cropped, "snip")

        RegionSelector(self.root, img, origin, done)

    def do_scroll(self) -> None:
        """Select an area, then the app scrolls it and stitches one tall image."""
        if self.selector_open or self.scroll_busy:
            return
        self.selector_open = True
        img, origin = grab.virtual_screen()

        def done(result):
            self.selector_open = False
            if result is None:
                return
            _cropped, box = result
            bbox = (box[0] + origin[0], box[1] + origin[1],
                    box[2] + origin[0], box[3] + origin[1])
            self.scroll_busy = True
            self.set_busy(True)
            self.notify("Scrolling capture running — hands off, Esc to stop")

            def work():
                try:
                    stitched = scroll.capture_scrolling(bbox, self.cfg)
                    if stitched is None:
                        self.notify("Scrolling capture: area too small")
                    else:
                        self.post(lambda: self.finish_capture(stitched, "scroll"))
                except Exception as e:
                    log.exception("scrolling capture failed")
                    self.notify(f"Scrolling capture failed: {e}")
                finally:
                    self.scroll_busy = False
                    self.post(lambda: self.set_busy(False))

            threading.Thread(target=work, daemon=True).start()

        RegionSelector(self.root, img, origin, done)

    def do_annotate(self) -> None:
        if self.annotator_open:
            return
        pngs = sorted(self.cfg["resolved_save_dir"].glob("*.png"),
                      key=lambda p: p.stat().st_mtime)
        if not pngs:
            self.notify("No captures to annotate yet")
            return
        self.annotator_open = True

        def closed():
            self.annotator_open = False

        try:
            Annotator(self.root, pngs[-1], self.notify, on_close=closed)
        except Exception:
            self.annotator_open = False
            raise

    def do_fullscreen(self) -> None:
        img, _ = grab.virtual_screen()
        self.finish_capture(img, "screen")

    def do_window(self) -> None:
        img = grab.grab_window()
        if img is None:
            self.notify("No window to capture")
            return
        self.finish_capture(img, "window")

    def do_fullpage(self, force_prompt: bool = False) -> None:
        if self.page_busy:
            self.notify("A full-page capture is already running")
            return
        if force_prompt:
            url = self.ask_url()
        else:
            source = self.fullpage_source_hwnd or active_browser.foreground_browser()
            self.fullpage_source_hwnd = None
            url = active_browser.read_url(source)
            if not url:
                self.notify("Open the web page in Chrome, Edge, Brave, or Firefox, then try Full page again")
                return
        if not url:
            return
        if url.lower().startswith("www."):
            url = "https://" + url

        self.page_busy = True
        self.set_busy(True)
        self.notify(f"Capturing full page: {url}")

        def work():
            target = None
            try:
                target = save.next_path("page", self.cfg["resolved_save_dir"], url)
                webpage.capture_page(url, target, self.cfg)
                with Image.open(target) as opened:
                    page_img = opened.copy()
                clip_note = ""
                if (self.cfg.get("copy_to_clipboard", True)
                        and page_img.height <= self.cfg.get("clipboard_max_height", 8000)):
                    try:
                        clip.copy_image(page_img)
                        clip_note = " · on clipboard"
                    except Exception:
                        clip_note = ""
                elif self.cfg.get("copy_to_clipboard", True):
                    clip_note = " · too tall for clipboard, file saved"
                self.beep()
                self.notify(f"{target.name}{clip_note}")
            except Exception as e:
                log.exception("full-page capture failed for %s", url)
                try:
                    if target is not None and target.exists():
                        target.unlink()
                except Exception:
                    pass
                self.notify(f"Full-page capture failed: {e}")
            finally:
                self.page_busy = False
                self.post(lambda: self.set_busy(False))

        threading.Thread(target=work, daemon=True).start()

    def ask_url(self) -> str | None:
        """Small dark URL prompt (dark mode always — bright white gives Di headaches)."""
        result = {"url": None}
        top = tk.Toplevel(self.root)
        top.title("Snip full page")
        top.configure(bg=INK, padx=18, pady=16)
        top.attributes("-topmost", True)
        top.resizable(False, False)

        tk.Label(top, text="Web page URL", bg=INK, fg=PAPER,
                 font=("Segoe UI", 11)).pack(anchor="w")
        entry = tk.Entry(top, width=58, bg="#221f20", fg=PAPER, insertbackground=PINK,
                         relief="flat", font=("Segoe UI", 11))
        entry.pack(pady=(6, 12), ipady=5)
        try:
            import pyperclip
            text = (pyperclip.paste() or "").strip()
            if URL_RE.match(text):
                entry.insert(0, text)
        except Exception:
            pass

        def ok(_e=None):
            result["url"] = entry.get().strip() or None
            top.destroy()

        def cancel(_e=None):
            top.destroy()

        row = tk.Frame(top, bg=INK)
        row.pack(anchor="e")
        tk.Button(row, text="Cancel", command=cancel, bg="#221f20", fg=PAPER,
                  relief="flat", padx=14, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(row, text="Capture", command=ok, bg=PINK, fg=INK,
                  relief="flat", padx=14, pady=4, font=("Segoe UI", 10, "bold")).pack(side="left")
        top.bind("<Return>", ok)
        top.bind("<Escape>", cancel)

        top.update_idletasks()
        x = (top.winfo_screenwidth() - top.winfo_width()) // 2
        y = (top.winfo_screenheight() - top.winfo_height()) // 3
        top.geometry(f"+{x}+{y}")
        entry.focus_force()
        top.grab_set()
        self.root.wait_window(top)
        return result["url"]

    # -- tray menu (called on pystray's thread) -----------------------------------

    def open_folder(self) -> None:
        d = self.cfg["resolved_save_dir"]
        d.mkdir(parents=True, exist_ok=True)
        import os
        os.startfile(d)

    def open_config(self) -> None:
        import os
        os.startfile(settings.APP_DIR / "config.toml")

    def open_login_browser(self) -> None:
        if self.page_busy:
            self.notify("Wait for the current page capture to finish")
            return
        self.notify("Opening the capture browser — log in, then close the window")

        def work():
            self.page_busy = True
            try:
                webpage.open_login_browser(self.cfg)
                self.notify("Logins saved for future captures")
            except Exception as e:
                self.notify(f"Browser error: {e}")
            finally:
                self.page_busy = False

        threading.Thread(target=work, daemon=True).start()

    def reload_config(self) -> None:
        self.cfg = settings.load()
        self.notify("Config reloaded")

    def quit(self) -> None:
        if self.menu_hotkey:
            self.menu_hotkey.close()
        self.icon.stop()
        self.post(self.root.quit)

    # -- wiring -----------------------------------------------------------------

    def run(self) -> None:
        self.icon.run_detached()
        self.poll()
        try:
            self.menu_hotkey = MenuHotkey(lambda: self.post(self.do_menu))
            log.info("capture started (only global shortcut: Ctrl+Shift+S; Windows registration)")
        except RuntimeError as exc:
            log.error("menu shortcut: %s", exc)
            self.notify(str(exc))
        try:
            self.root.mainloop()
        finally:
            if self.menu_hotkey:
                self.menu_hotkey.close()
        log.info("capture exiting")


def _already_running() -> bool:
    """Single-instance guard: two instances double-handle every hotkey."""
    ctypes.windll.kernel32.CreateMutexW(None, False, "SwayRise.Capture.SingleInstance")
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


if __name__ == "__main__":
    if _already_running():
        log.info("another instance is already running; exiting")
    else:
        try:
            App().run()
        except Exception:
            log.exception("fatal startup error")
            raise
