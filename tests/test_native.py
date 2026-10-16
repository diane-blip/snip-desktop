"""Opt-in controlled desktop tests. Never stop or register the installed Snip shortcut."""

import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import win32clipboard
import win32gui
from PIL import Image

import active_browser
import capture
from annotate import Annotator
from palette import Palette
from region import RegionSelector
from url_prompt import URLPrompt
from windows_ui import place


@unittest.skipUnless(os.environ.get("SNIP_INTERACTIVE") == "1", "interactive desktop fixture")
class NativeTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_negative_window_placement(self):
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        place(top, 300, 200, -400, -250)
        self.root.update()
        self.assertEqual((top.winfo_rootx(), top.winfo_rooty()), (-400, -250))

    def test_url_enter_respects_focused_cancel_and_entry(self):
        prompt = URLPrompt(self.root)
        self.root.update()
        prompt.entry.insert(0, "https://example.com/")
        prompt.cancel_button.focus_force()
        prompt.cancel_button.event_generate("<Return>")
        self.root.update()
        self.assertIsNone(prompt.result)
        self.assertFalse(prompt.top.winfo_exists())
        prompt = URLPrompt(self.root)
        self.root.update()
        prompt.entry.insert(0, "https://example.com/")
        prompt.entry.focus_force()
        prompt.entry.event_generate("<Return>")
        self.root.update()
        self.assertEqual(prompt.result, "https://example.com/")

    def test_narrow_editor_can_reach_right_edge_of_large_image(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.png"
            Image.new("RGB", (1100, 700), "white").save(path)
            editor = Annotator(self.root, path, Mock(), cfg={"copy_to_clipboard": False})
            editor.top.geometry("480x300+100+100")
            self.root.update()
            editor.canvas.xview_moveto(1.0)
            editor.canvas.yview_moveto(1.0)
            self.root.update()
            self.assertAlmostEqual(editor.canvas.xview()[1], 1.0)
            self.assertAlmostEqual(editor.canvas.yview()[1], 1.0)
            self.assertGreaterEqual(editor.top.winfo_width(), editor.top.minsize()[0])
            editor.close(discard=True)

    def test_real_window_capture_and_scrolling_fixture(self):
        import threading
        import time

        import numpy as np
        import win32api
        import win32process
        from PIL import ImageTk

        import grab
        import scroll

        top = tk.Toplevel(self.root)
        top.geometry("400x300+100+100")
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        canvas = tk.Canvas(top, width=400, height=300, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        rng = np.random.default_rng(7)
        rows = rng.integers(25, 220, (1600, 1, 3), dtype=np.uint8)
        pixels = np.repeat(rows, 400, axis=1)
        photo = ImageTk.PhotoImage(Image.fromarray(pixels))
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas.configure(scrollregion=(0, 0, 400, 1600), yscrollincrement=1)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-e.delta // 120 * 80, "units"))
        self.root.update()
        hwnd = win32gui.GetAncestor(top.winfo_id(), 2)
        top.lift()
        # Desktop runners may start in the background. Attach only long enough
        # to focus this owned fixture; detach before sending any wheel input.
        own_thread = win32api.GetCurrentThreadId()
        foreground_thread, _ = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())
        attached = own_thread != foreground_thread
        if attached:
            win32process.AttachThreadInput(own_thread, foreground_thread, True)
        try:
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if attached:
                win32process.AttachThreadInput(own_thread, foreground_thread, False)
        self.root.after(150, self.root.quit)
        self.root.mainloop()
        self.assertEqual(win32gui.GetForegroundWindow(), hwnd)
        result = grab.grab_window(hwnd)
        self.assertEqual(result.size, (400, 300))
        self.assertEqual(result.getpixel((10, 10)), tuple(int(n) for n in pixels[10, 10]))
        values = []
        failures = []
        cfg = {
            "max_pixels": 1000000,
            "scroll": {"wheel_ticks": 1, "settle_ms": 150, "max_height": 700, "max_steps": 5},
        }

        def work():
            try:
                values.append(scroll.capture_scrolling((100, 100, 500, 400), cfg))
            except Exception as exc:
                failures.append(exc)

        worker = threading.Thread(target=work)
        worker.start()
        while worker.is_alive():
            self.root.update()
            time.sleep(0.01)
        worker.join()
        top.destroy()
        self.assertEqual(failures, [])
        self.assertEqual(values[0].size, (400, 700))
        np.testing.assert_array_equal(np.array(values[0]), pixels[:700])

    def test_tray_lifecycle_without_production_shortcut(self):
        import subprocess
        import sys

        # Keep Tk interpreter teardown isolated from other fixture roots.
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import capture; app=capture.App(); app.root.after(350,app.quit); app.run(register_hotkey=False); assert app.state=='closing' and app.menu_hotkey is None",
            ],
            cwd=capture.settings.APP_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_region_drag_preserves_source_pixels_and_cancel_is_once(self):
        image = Image.new("RGB", (400, 300), (20, 90, 120))
        done = Mock()
        selector = RegionSelector(self.root, image, (50, 50), done)
        selector.on_press(SimpleNamespace(x=20, y=30))
        selector.on_move(SimpleNamespace(x=120, y=130))
        selector.on_release(SimpleNamespace(x=120, y=130))
        selector.on_cancel()
        done.assert_called_once()
        crop, box = done.call_args.args[0]
        self.assertEqual(box, (20, 30, 120, 130))
        self.assertEqual(crop.size, (100, 100))
        self.assertEqual(crop.getpixel((0, 0)), (20, 90, 120))

    def test_palette_small_work_area_all_actions_remain_reachable(self):
        callbacks = [Mock() for _ in range(7)]
        with patch("palette.work_area", return_value=(0, 0, 640, 400)):
            popup = Palette(
                self.root,
                [(str(i), f"Action {i}", cb) for i, cb in enumerate(callbacks)],
                lambda cb: cb() if cb else None,
            )
        self.root.update()
        self.assertLessEqual(popup.top.winfo_height(), 384)
        popup.buttons[-1].focus_set()
        self.root.update()
        popup.buttons[-1].invoke()
        callbacks[-1].assert_called_once()

    def test_instance_guard_retains_handle_and_blocks_second_copy(self):
        first = capture.InstanceGuard()
        try:
            second = capture.InstanceGuard()
            try:
                self.assertTrue(second.already_running)
            finally:
                second.close()
        finally:
            first.close()

    def test_browser_address_lookup_leaves_clipboard_unchanged(self):
        from playwright.sync_api import sync_playwright

        with tempfile.TemporaryDirectory() as folder, sync_playwright() as driver:
            ctx = driver.chromium.launch_persistent_context(
                folder,
                headless=False,
                args=["--force-renderer-accessibility"],
                viewport={"width": 800, "height": 600},
            )
            try:
                page = ctx.pages[0]
                # Use the local fixture server from the full-page tests.
                import sys

                sys.path.insert(0, str(Path(__file__).parent))
                import threading
                from http.server import ThreadingHTTPServer

                from test_webpage import _PageHandler

                server = ThreadingHTTPServer(("127.0.0.1", 0), _PageHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}/"
                    page.goto(url)
                    page.evaluate("document.title='Snip address fixture'")
                    page.wait_for_timeout(500)
                    windows = []
                    win32gui.EnumWindows(
                        lambda hwnd, unused: (
                            windows.append(hwnd)
                            if "Snip address fixture" in win32gui.GetWindowText(hwnd)
                            else None
                        ),
                        None,
                    )
                    self.assertTrue(windows)
                    before = win32clipboard.GetClipboardSequenceNumber()
                    result = active_browser.read_url(windows[0])
                    self.assertEqual(result, url)
                    self.assertEqual(win32clipboard.GetClipboardSequenceNumber(), before)
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()
            finally:
                ctx.close()
