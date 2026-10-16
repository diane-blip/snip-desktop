import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import active_browser
import save


class ActiveBrowserTests(unittest.TestCase):
    def test_url_validation_rejects_local_files_credentials_and_bad_ports(self):
        for value in (
            "file:///C:/private",
            "https://user:secret@example.com",
            "https://:secret@example.com",
            "https://@example.com",
            "javascript:1",
            "https://example.com:99999",
            "https://example.com/a\nb",
        ):
            self.assertIsNone(active_browser.normalize_url(value))
        self.assertEqual(active_browser.normalize_url("www.example.com"), "https://www.example.com")

    @patch("active_browser.win32gui")
    def test_rejects_non_browser_window(self, gui):
        gui.IsWindow.return_value = True
        gui.GetClassName.return_value = "Notepad"
        self.assertIsNone(active_browser.read_url(42))


class SaveTests(unittest.TestCase):
    def test_next_path_does_not_write_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save.next_path("page", Path(tmp))
            self.assertFalse(path.exists())

    def test_save_png_writes_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save.save_png(Image.new("RGB", (5, 7)), "snip", Path(tmp))
            self.assertTrue(path.exists())
            with Image.open(path) as image:
                self.assertEqual(image.size, (5, 7))


if __name__ == "__main__":
    unittest.main()
