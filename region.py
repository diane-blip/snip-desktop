"""Frozen-frame region selector.

The screen is grabbed FIRST, then shown fullscreen darkened; dragging reveals
the bright crop (Snipping Tool feel). Because the selection is cropped from the
already-taken grab, there are no timing games and the overlay can never appear
in the shot.
"""
import tkinter as tk

from PIL import Image, ImageEnhance, ImageTk

BORDER = "#F0BDCE"  # softened brand pink
DARKEN = 0.35


class RegionSelector:
    """Shows the overlay; calls done((cropped_image, box) | None) and destroys
    itself. box is (left, top, right, bottom) in image coordinates."""

    def __init__(self, root: tk.Tk, img: Image.Image, origin: tuple[int, int], done):
        self.img = img
        self.done = done
        self.start = None
        self.rect_id = None
        self.reveal_id = None
        self.reveal_photo = None  # keep a reference or Tk drops the image
        self.label_id = None
        self.finished = False

        left, top = origin
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.geometry(f"{img.width}x{img.height}+{left}+{top}")
        self.top.attributes("-topmost", True)
        self.top.configure(cursor="crosshair")

        dark = ImageEnhance.Brightness(img).enhance(DARKEN)
        self.dark_photo = ImageTk.PhotoImage(dark)
        self.canvas = tk.Canvas(
            self.top, width=img.width, height=img.height,
            highlightthickness=0, bd=0, bg="#111111",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, anchor="nw", image=self.dark_photo)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", self.on_cancel)
        self.top.bind("<ButtonPress-3>", self.on_cancel)

        self.top.focus_force()
        self.top.grab_set()

    # -- events ---------------------------------------------------------------

    def on_press(self, e):
        self.start = (e.x, e.y)

    def on_move(self, e):
        if not self.start:
            return
        box = self._box(e)
        if self.reveal_id:
            self.canvas.delete(self.reveal_id)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        if self.label_id:
            self.canvas.delete(self.label_id)
        w, h = box[2] - box[0], box[3] - box[1]
        if w > 0 and h > 0:
            self.reveal_photo = ImageTk.PhotoImage(self.img.crop(box))
            self.reveal_id = self.canvas.create_image(
                box[0], box[1], anchor="nw", image=self.reveal_photo
            )
        self.rect_id = self.canvas.create_rectangle(*box, outline=BORDER, width=2)
        label_y = box[1] - 22 if box[1] > 26 else box[3] + 6
        self.label_id = self.canvas.create_text(
            box[0] + 4, label_y, anchor="nw",
            text=f"{w} x {h}", fill=BORDER, font=("Segoe UI", 11, "bold"),
        )

    def on_release(self, e):
        if not self.start:
            return
        box = self._box(e)
        if box[2] - box[0] < 4 or box[3] - box[1] < 4:
            self._finish(None)
        else:
            self._finish((self.img.crop(box), box))

    def on_cancel(self, _e=None):
        self._finish(None)

    # -- helpers ----------------------------------------------------------------

    def _box(self, e) -> tuple[int, int, int, int]:
        x0, y0 = self.start
        x1 = max(0, min(e.x, self.img.width))
        y1 = max(0, min(e.y, self.img.height))
        return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    def _finish(self, result):
        if self.finished:
            return
        self.finished = True
        try:
            self.top.grab_release()
            self.top.destroy()
        except Exception:
            pass
        self.done(result)
