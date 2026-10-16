"""Read browser chrome through UI Automation, without keys or clipboard access."""

import time
from collections import deque
from urllib.parse import urlsplit

import win32gui

BROWSER_CLASSES = {"Chrome_WidgetWin_1", "MozillaWindowClass"}
ADDRESS_IDS = {"address and search bar", "urlbar-input", "urlbar"}
ADDRESS_NAMES = {"address and search bar", "search or enter address", "address and search"}


def normalize_url(value):
    value = value.strip()
    if value.startswith("www."):
        value = "https://" + value
    try:
        parts = urlsplit(value)
        valid = (
            parts.scheme in {"http", "https"}
            and parts.hostname
            and parts.username is None
            and parts.password is None
        )
        port = parts.port  # Validate malformed port syntax too.
        if port is not None and not 1 <= port <= 65535:
            return None
        if any(ord(char) <= 32 for char in value):
            return None
        return value if valid else None
    except ValueError:
        return None


def foreground_browser():
    hwnd = win32gui.GetForegroundWindow()
    return hwnd if hwnd and win32gui.GetClassName(hwnd) in BROWSER_CLASSES else None


def read_url(hwnd):
    """Read only known address controls outside page documents; otherwise return None.

    Call in a worker. No page-content edits, focus changes or clipboard writes.
    Unsupported/localized browser controls use the explicit URL prompt instead.
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    if win32gui.GetClassName(hwnd) not in BROWSER_CLASSES:
        return None
    import comtypes
    from comtypes.client import CreateObject, GetModule

    comtypes.CoInitialize()
    try:
        module = GetModule("UIAutomationCore.dll")
        automation = CreateObject(module.CUIAutomation8, interface=module.IUIAutomation2)
        automation.ConnectionTimeout = 500
        automation.TransactionTimeout = 500
        walker = automation.ControlViewWalker
        pending = deque([automation.ElementFromHandle(hwnd)])
        visited = 0
        deadline = time.monotonic() + 5
        while pending and visited < 200 and time.monotonic() < deadline:
            element = pending.popleft()
            visited += 1
            kind = element.CurrentControlType
            if kind == 50030:  # Read URL metadata only; never inspect page inputs.
                if not element.CurrentIsOffscreen:
                    try:
                        pattern = element.GetCurrentPattern(10002).QueryInterface(
                            module.IUIAutomationValuePattern
                        )
                        url = normalize_url(pattern.CurrentValue or "")
                        if url:
                            return url
                    except comtypes.COMError:
                        pass
                continue
            identity = (element.CurrentAutomationId or "").casefold()
            name = (element.CurrentName or "").casefold()
            if kind in {50003, 50004} and (identity in ADDRESS_IDS or name in ADDRESS_NAMES):
                pattern = element.GetCurrentPattern(10002).QueryInterface(
                    module.IUIAutomationValuePattern
                )
                url = normalize_url(pattern.CurrentValue or "")
                if url:
                    return url
            child = walker.GetFirstChildElement(element)
            while child and len(pending) + visited < 200 and time.monotonic() < deadline:
                pending.append(child)
                child = walker.GetNextSiblingElement(child)
        return None
    except (OSError, comtypes.COMError):
        return None
    finally:
        comtypes.CoUninitialize()
