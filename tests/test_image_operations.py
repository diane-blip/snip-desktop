import unittest

import numpy as np
from PIL import Image

from annotate import render
from scroll import _sig, find_offset, stitch


class ScrollTests(unittest.TestCase):
    def test_finds_known_vertical_scroll(self):
        rng = np.random.default_rng(7)
        content = rng.integers(0, 256, (720, 96, 3), dtype=np.uint8)
        first = content[:480]
        second = content[135:615]
        offset, error = find_offset(_sig(first), _sig(second))
        self.assertEqual(offset, 135)
        self.assertLess(error, 0.01)

    def test_stitch_preserves_all_rows(self):
        a = np.zeros((10, 8, 3), dtype=np.uint8)
        b = np.full((7, 8, 3), 255, dtype=np.uint8)
        self.assertEqual(stitch([a, b]).size, (8, 17))


class AnnotationTests(unittest.TestCase):
    def test_render_keeps_original_untouched(self):
        base = Image.new("RGB", (120, 90), "white")
        result = render(base, [("box", 10, 10, 70, 60), ("arrow", 5, 80, 100, 20)])
        self.assertEqual(base.getpixel((10, 10)), (255, 255, 255))
        self.assertNotEqual(result.getpixel((10, 10)), (255, 255, 255))

    def test_blur_keeps_dimensions(self):
        base = Image.effect_noise((100, 100), 90).convert("RGB")
        result = render(base, [("blur", 10, 10, 80, 80)])
        self.assertEqual(result.size, base.size)
        self.assertNotEqual(
            result.crop((10, 10, 80, 80)).tobytes(), base.crop((10, 10, 80, 80)).tobytes()
        )


if __name__ == "__main__":
    unittest.main()
