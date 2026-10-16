"""Copy a PIL image to the Windows clipboard as a DIB (what Paint, Word,
browsers, Slack etc. all paste)."""
import io
import time

import win32clipboard


def copy_image(img) -> None:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "BMP")
    data = buf.getvalue()[14:]  # strip the 14-byte BITMAPFILEHEADER -> CF_DIB payload

    # Another app can briefly hold the clipboard; retry a few times.
    last_err = None
    for _ in range(4):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                return
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            last_err = e
            time.sleep(0.1)
    raise RuntimeError(f"Clipboard busy: {last_err}")
