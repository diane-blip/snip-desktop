import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import active_browser
import save


class ActiveBrowserTests(unittest.TestCase):
    @patch("active_browser.time.sleep")
    @patch("active_browser.keyboard.send")
    @patch("active_browser.pyperclip")
    @patch("active_browser.win32gui")
    def test_reads_active_browser_address(self, gui, clipboard, send, _sleep):
        gui.IsWindow.return_value = True
        gui.GetClassName.return_value = "Chrome_WidgetWin_1"
        clipboard.paste.return_value = "https://example.com/a"

        self.assertEqual(active_browser.read_url(42), "https://example.com/a")
        self.assertEqual(send.call_args_list[0].args[0], "ctrl+l")
        self.assertEqual(send.call_args_list[1].args[0], "ctrl+c")
        self.assertEqual(send.call_args_list[-1].args[0], "esc")

    @patch("active_browser.win32gui")
    def test_rejects_non_browser_window(self, gui):
        gui.IsWindow.return_value = True
        gui.GetClassName.return_value = "Notepad"
        self.assertIsNone(active_browser.read_url(42))


class SaveTests(unittest.TestCase):
    def test_next_path_does_not_write_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save.next_path("page", Path(tmp), "https://example.com")
            self.assertFalse(path.exists())

    def test_save_png_writes_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save.save_png(Image.new("RGB", (5, 7)), "snip", Path(tmp))
            self.assertTrue(path.exists())
            with Image.open(path) as image:
                self.assertEqual(image.size, (5, 7))


if __name__ == "__main__":
    unittest.main()
