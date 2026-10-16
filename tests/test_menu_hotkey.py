import threading
import unittest

from hotkey import MenuHotkey


class TestHotkey(MenuHotkey):
    key = 0x87  # F24. Never register the installed application's Ctrl+Shift+S.


class MenuHotkeyTests(unittest.TestCase):
    def test_native_conflict_and_release(self):
        first = TestHotkey(lambda: None)
        third = None
        try:
            self.assertTrue(first.registered)
            with self.assertRaisesRegex(RuntimeError, "Ctrl\\+Shift\\+S unavailable"):
                TestHotkey(lambda: None)
            first.close()
            third = TestHotkey(lambda: None)
            self.assertTrue(third.registered)
        finally:
            first.close()
            if third:
                third.close()

    def test_windows_message_dispatch_and_clean_exit(self):
        arrived = threading.Event()
        hotkey = TestHotkey(arrived.set)
        try:
            self.assertTrue(
                hotkey.user32.PostThreadMessageW(
                    hotkey.thread_id,
                    0x0312,
                    hotkey.identifier,
                    hotkey.modifiers | (hotkey.key << 16),
                )
            )
            self.assertTrue(arrived.wait(2))
        finally:
            hotkey.close()
        self.assertFalse(hotkey.registered)
        self.assertFalse(hotkey.thread.is_alive())
