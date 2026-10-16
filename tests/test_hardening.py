import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

import capture
import clip
import save
import settings
from annotate import Annotator, render


class SettingsTests(unittest.TestCase):
    def load_override(self, text):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.toml").write_bytes((settings.APP_DIR / "config.toml").read_bytes())
            (root / "config.local.toml").write_text(text)
            with patch.object(settings, "APP_DIR", root):
                return settings.load()

    def test_local_override_preserves_defaults(self):
        cfg = self.load_override('sounds = false\nsave_dir = "captures"')
        self.assertFalse(cfg["sounds"])
        self.assertEqual(cfg["fullpage"]["viewport_width"], 1440)
        self.assertEqual(cfg["resolved_save_dir"].name, "captures")

    def test_invalid_values_and_unknown_fields_fail(self):
        for text in (
            "unknown = true",
            "sounds = 1",
            "max_pixels = true",
            "[scroll]\nmax_steps = 9999",
            "[fullpage]\nviewport_width = 0",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.load_override(text)


class AtomicSaveTests(unittest.TestCase):
    def test_failed_write_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(Image.Image, "save", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    save.save_png(Image.new("RGB", (8, 8)), "snip", root)
            self.assertEqual(list(root.iterdir()), [])

    def test_existing_file_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "original.png"
            target.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                save.write_png(Image.new("RGB", (8, 8)), target)
            self.assertEqual(target.read_bytes(), b"original")
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_concurrent_names_are_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            names = {save.next_path("page", Path(folder)) for _ in range(100)}
            self.assertEqual(len(names), 100)


class AnnotationTests(unittest.TestCase):
    def test_redaction_discards_selected_pixels_in_export(self):
        image = Image.effect_noise((80, 80), 50).convert("RGB")
        output = render(image, [("redact", 10, 10, 50, 50)])
        self.assertEqual(output.crop((10, 10, 51, 51)).getextrema(), ((0, 0), (0, 0), (0, 0)))
        self.assertNotEqual(image.tobytes(), output.tobytes())
        self.assertEqual(output.getpixel((0, 0)), image.getpixel((0, 0)))

    def test_off_image_operations_are_clamped(self):
        output = render(Image.new("RGB", (40, 30), "white"), [("redact", -50, -50, 500, 500)])
        self.assertEqual(output.getextrema(), ((0, 0), (0, 0), (0, 0)))

    def test_save_respects_clipboard_off_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            app = Annotator.__new__(Annotator)
            app.path = Path(folder) / "source.png"
            app.base = Image.new("RGB", (30, 30), "white")
            app.base.save(app.path)
            original = app.path.read_bytes()
            app.ops = [("redact", 0, 0, 10, 10)]
            app.cfg = {"copy_to_clipboard": False}
            app.notify = Mock()
            app.close = Mock()
            with patch("clip.copy_image") as copy:
                app.save()
            copy.assert_not_called()
            self.assertEqual(app.path.read_bytes(), original)
            self.assertEqual(len(list(Path(folder).glob("*.png"))), 2)


class LifecycleTests(unittest.TestCase):
    def app(self):
        app = capture.App.__new__(capture.App)
        app.cfg = settings.load()
        app.state = "idle"
        app.icon = Mock()
        app.root = Mock()
        app.notify = Mock()
        app.q = queue.Queue()
        return app

    def test_overlapping_job_reload_and_quit_are_refused(self):
        app = self.app()
        app.state = "web capture"
        work = Mock()
        with patch("capture.settings.load") as load:
            app.job("other", work)
            app.quit()
            app.reload_config()
        work.assert_not_called()
        load.assert_not_called()
        app.root.quit.assert_not_called()
        self.assertEqual(app.state, "web capture")

    def test_worker_completion_is_queued_and_uses_config_snapshot(self):
        app = self.app()
        release = threading.Event()

        def work(cfg):
            release.wait(2)
            return cfg["sounds"]

        complete = Mock()
        app.job("fixture", work, complete)
        self.assertEqual(app.state, "fixture")
        app.cfg["sounds"] = False
        release.set()
        finish = app.q.get(timeout=3)
        complete.assert_not_called()
        finish()
        self.assertTrue(complete.call_args.args[0])
        self.assertEqual(app.state, "idle")

    def test_invalid_reload_keeps_previous_config(self):
        app = self.app()
        old = app.cfg
        with patch("capture.settings.load", side_effect=ValueError), self.assertRaises(ValueError):
            app.reload_config()
        self.assertIs(app.cfg, old)

    def test_clipboard_failure_keeps_saved_capture(self):
        app = self.app()
        app.beep = Mock()
        with tempfile.TemporaryDirectory() as folder:
            app.cfg["resolved_save_dir"] = Path(folder)
            with patch("capture.clip.copy_image", side_effect=OSError):
                app.finish_capture(Image.new("RGB", (4, 4)), "snip")
            self.assertTrue(app.last_capture.exists())
            self.assertIn("file saved", app.notify.call_args.args[0])


class ClipboardTests(unittest.TestCase):
    def test_clipboard_payload_decodes_to_original_pixels(self):
        import io
        import struct

        image = Image.new("RGB", (3, 2), (24, 85, 130))
        image.putpixel((2, 1), (240, 10, 35))
        with patch("clip.win32clipboard") as clipboard:
            clip.copy_image(image)
        data = clipboard.SetClipboardData.call_args.args[1]
        header = b"BM" + struct.pack("<IHHI", len(data) + 14, 0, 0, 54)
        with Image.open(io.BytesIO(header + data)) as decoded:
            self.assertEqual(decoded.size, image.size)
            self.assertEqual(decoded.tobytes(), image.tobytes())
        clipboard.CloseClipboard.assert_called_once()

    def test_failed_transfer_closes_clipboard(self):
        with patch("clip.win32clipboard") as clipboard, patch("clip.time.sleep"):
            clipboard.SetClipboardData.side_effect = OSError
            with self.assertRaises(RuntimeError):
                clip.copy_image(Image.new("RGB", (2, 2)))
        self.assertEqual(clipboard.CloseClipboard.call_count, 4)
