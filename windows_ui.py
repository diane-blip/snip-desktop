"""Physical desktop geometry, including monitors with negative origins."""

import ctypes
from ctypes import wintypes


def work_area(root):
    class MonitorInfo(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("monitor", wintypes.RECT),
            ("work", wintypes.RECT),
            ("flags", wintypes.DWORD),
        ]

    user = ctypes.windll.user32
    user.MonitorFromPoint.argtypes = (wintypes.POINT, wintypes.DWORD)
    user.MonitorFromPoint.restype = wintypes.HANDLE
    user.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
    monitor = user.MonitorFromPoint(wintypes.POINT(root.winfo_pointerx(), root.winfo_pointery()), 2)
    info = MonitorInfo(size=ctypes.sizeof(MonitorInfo))
    if user.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return info.work.left, info.work.top, info.work.right, info.work.bottom
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def place(top, width, height, x, y):
    top.geometry(f"{width}x{height}")
    top.update_idletasks()
    user = ctypes.windll.user32
    user.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
    user.GetAncestor.restype = wintypes.HWND
    user.SetWindowPos.argtypes = (
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    )
    hwnd = user.GetAncestor(top.winfo_id(), 2)
    if not user.SetWindowPos(hwnd, None, x, y, width, height, 0x0004 | 0x0010):
        raise OSError("Window positioning failed")
