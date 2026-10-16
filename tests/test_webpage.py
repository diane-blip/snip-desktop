import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image

import webpage


class _PageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/missing":
            self.send_error(404)
            return
        body = b"""<!doctype html><style>body{margin:0}.block{height:900px}</style>
        <div class=block style='background:#2563a6'></div>
        <div class=block style='background:#90d5cf'></div>
        <div class=block style='background:#111'></div>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class FullPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _PageHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_http_error_does_not_publish_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = {
                "resolved_profile_dir": root / "profile",
                "fullpage": {"viewport_width": 800, "timeout_seconds": 10, "settle_ms": 0},
            }
            with self.assertRaises(RuntimeError):
                webpage.capture_page(
                    f"http://127.0.0.1:{self.server.server_port}/missing", root / "page.png", cfg
                )
            self.assertFalse((root / "page.png").exists())

    def test_oversized_page_does_not_publish_a_partial_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = {
                "resolved_profile_dir": root / "profile",
                "fullpage": {
                    "viewport_width": 800,
                    "timeout_seconds": 10,
                    "settle_ms": 0,
                    "max_height": 1000,
                },
            }
            with self.assertRaises(ValueError):
                webpage.capture_page(
                    f"http://127.0.0.1:{self.server.server_port}/", root / "page.png", cfg
                )
            self.assertFalse((root / "page.png").exists())

    def test_captures_entire_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "page.png"
            cfg = {
                "resolved_profile_dir": root / "profile",
                "fullpage": {"viewport_width": 800, "timeout_seconds": 10, "settle_ms": 50},
            }
            url = f"http://127.0.0.1:{self.server.server_port}/"
            webpage.capture_page(url, out, cfg)
            with Image.open(out) as image:
                self.assertEqual(image.width, 800)
                self.assertGreaterEqual(image.height, 2700)


if __name__ == "__main__":
    unittest.main()
