"""One Windows-owned shortcut, with explicit conflict and release handling."""

import ctypes
import threading
from ctypes import wintypes


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
        self.user32.RegisterHotKey.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.GetMessageW.restype = ctypes.c_int
        self.user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
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
