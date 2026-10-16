"""Non-destructive annotation editor; every save creates a separate PNG."""

import math
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageDraw, ImageFilter, ImageTk

import save
from theme import MARKUP, SELECTED, button_style
from theme import ROW as PANEL
from theme import SURFACE as INK
from theme import TEXT as PAPER
from windows_ui import work_area

BLUR_RADIUS = 14


def render(base: Image.Image, ops: list) -> Image.Image:
    img = base.copy()
    draw = ImageDraw.Draw(img)
    w = max(4, base.width // 400)  # stroke width scales with image size
    for kind, x0, y0, x1, y1 in ops:
        x0, x1 = (max(0, min(int(x), base.width - 1)) for x in (x0, x1))
        y0, y1 = (max(0, min(int(y), base.height - 1)) for y in (y0, y1))
        if kind == "blur":
            box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            if box[2] - box[0] > 2 and box[3] - box[1] > 2:
                img.paste(img.crop(box).filter(ImageFilter.GaussianBlur(BLUR_RADIUS)), box)
                draw = ImageDraw.Draw(img)
        elif kind == "redact":
            draw.rectangle((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), fill="#000000")
        elif kind == "box":
            draw.rectangle(
                (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), outline=MARKUP, width=w
            )
        elif kind == "arrow":
            draw.line((x0, y0, x1, y1), fill=MARKUP, width=w)
            ang = math.atan2(y1 - y0, x1 - x0)
            head = w * 4.5
            for spread in (math.radians(155), math.radians(-155)):
                draw.line(
                    (
                        x1,
                        y1,
                        x1 + head * math.cos(ang + spread),
                        y1 + head * math.sin(ang + spread),
                    ),
                    fill=MARKUP,
                    width=w,
                )
    return img


class Annotator:
    def __init__(self, root: tk.Tk, path: Path, notify, on_close=None, cfg=None):
        self.path = path
        self.notify = notify
        self.on_close = on_close
        self.cfg = cfg or {}
        with Image.open(path) as source:
            if source.width * source.height > self.cfg.get("max_pixels", 40000000):
                raise ValueError("Image exceeds the annotation size limit")
            self.base = source.convert("RGB")
        self.closed = False
        self.ops: list = []
        self.tool = "arrow"
        self.start = None
        self.preview_id = None
        self.tool_buttons = {}

        left, upper, right, bottom = work_area(root)
        screen_w, screen_h = right - left, bottom - upper
        self.scale = min(
            1.0, (screen_w - 80) / self.base.width, (screen_h * 4.0) / self.base.height
        )  # cap width, allow tall
        self.disp_w = int(self.base.width * self.scale)
        self.disp_h = int(self.base.height * self.scale)

        self.top = tk.Toplevel(root)
        self.top.title(f"Annotate: {path.name}")
        self.top.configure(bg=INK)
        view_h = min(screen_h - 180, max(180, self.disp_h))
        self.top.geometry(f"{min(screen_w - 40, max(680, self.disp_w + 40))}x{view_h + 124}")

        bar = tk.Frame(self.top, bg=INK)
        bar.pack(fill="x", padx=10, pady=8)
        for name, label in (
            ("arrow", "Arrow"),
            ("box", "Box"),
            ("blur", "Blur"),
            ("redact", "Redact"),
        ):
            b = tk.Button(
                bar, text=label, **button_style(), command=lambda n=name: self.set_tool(n)
            )
            b.pack(side="left", padx=(0, 6))
            self.tool_buttons[name] = b
        tk.Button(bar, text="Undo", **button_style(), command=self.undo).pack(
            side="left", padx=(12, 0)
        )
        actions = tk.Frame(self.top, bg=INK)
        actions.pack(fill="x", padx=12, pady=(0, 8))
        guidance = tk.Label(
            actions,
            text="Redact covers pixels. Blur only softens them.",
            bg=INK,
            fg=PAPER,
            font=("Segoe UI", 10),
            justify="left",
        )
        guidance.pack(side="left")
        save_button = tk.Button(
            actions,
            text="Save + copy" if self.cfg.get("copy_to_clipboard", True) else "Save PNG",
            **button_style(True),
            command=self.save,
        )
        save_button.pack(side="right")
        actions.bind(
            "<Configure>",
            lambda e: guidance.configure(
                wraplength=max(120, e.width - save_button.winfo_reqwidth() - 16)
            ),
        )
        self.set_tool("arrow")

        frame = tk.Frame(self.top, bg=INK)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.canvas = tk.Canvas(
            frame,
            width=self.disp_w,
            height=view_h,
            bg=INK,
            highlightthickness=0,
            scrollregion=(0, 0, self.disp_w, self.disp_h),
        )
        vbar = tk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        hbar = tk.Scrollbar(frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        hbar.pack(side="bottom", fill="x")
        vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.photo = None
        self.img_id = self.canvas.create_image(0, 0, anchor="nw")
        self.refresh()

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind(
            "<MouseWheel>", lambda e: self.canvas.yview_scroll(-e.delta // 120, "units")
        )
        self.top.bind("<Control-z>", lambda e: self.undo())
        self.top.bind("<Control-s>", lambda e: self.save())
        self.top.bind("<Escape>", lambda e: self.close())
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.top.update_idletasks()
        self.top.minsize(
            min(screen_w - 40, max(480, bar.winfo_reqwidth() + 20)), min(300, screen_h - 40)
        )
        self.top.lift()
        self.top.focus_force()

    # -- tools / render ---------------------------------------------------------

    def set_tool(self, name: str) -> None:
        self.tool = name
        for n, b in self.tool_buttons.items():
            b.configure(
                bg=SELECTED if n == name else PANEL,
                fg=INK if n == name else PAPER,
                relief="sunken" if n == name else "flat",
            )

    def refresh(self) -> None:
        img = render(self.base, self.ops)
        if self.scale < 1.0:
            img = img.resize((self.disp_w, self.disp_h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.itemconfigure(self.img_id, image=self.photo)

    def undo(self) -> None:
        if self.ops:
            self.ops.pop()
            self.refresh()

    # -- mouse -----------------------------------------------------------------

    def _pt(self, e) -> tuple[float, float]:
        return (
            max(0, min(self.canvas.canvasx(e.x), self.disp_w - 1)),
            max(0, min(self.canvas.canvasy(e.y), self.disp_h - 1)),
        )

    def on_press(self, e) -> None:
        self.start = self._pt(e)

    def on_move(self, e) -> None:
        if not self.start:
            return
        x0, y0 = self.start
        x1, y1 = self._pt(e)
        if self.preview_id:
            self.canvas.delete(self.preview_id)
        if self.tool == "arrow":
            self.preview_id = self.canvas.create_line(
                x0, y0, x1, y1, fill=MARKUP, width=3, arrow=tk.LAST, arrowshape=(14, 18, 6)
            )
        else:
            dash = (5, 3) if self.tool == "blur" else None
            self.preview_id = self.canvas.create_rectangle(
                x0, y0, x1, y1, outline=MARKUP, width=2, dash=dash
            )

    def on_release(self, e) -> None:
        if not self.start:
            return
        x0, y0 = self.start
        x1, y1 = self._pt(e)
        self.start = None
        if self.preview_id:
            self.canvas.delete(self.preview_id)
            self.preview_id = None
        if abs(x1 - x0) < 3 and abs(y1 - y0) < 3:
            return
        s = self.scale
        self.ops.append((self.tool, int(x0 / s), int(y0 / s), int(x1 / s), int(y1 / s)))
        self.refresh()

    # -- save / close -------------------------------------------------------------

    def save(self) -> None:
        import clip

        img = render(self.base, self.ops)
        try:
            out = save.save_png(img, "annotated", self.path.parent)
        except OSError:
            self.notify("Could not save. Your edits remain open; check the folder and try again.")
            return
        note = ""
        try:
            if self.cfg.get("copy_to_clipboard", True):
                if img.height <= self.cfg.get("clipboard_max_height", 8000):
                    clip.copy_image(img)
                    note = " · on clipboard"
                else:
                    note = " · too tall for clipboard, file saved"
        except Exception:
            note = " · clipboard unavailable, file saved"
        self.notify(f"{out.name}{note}")
        self.close(discard=True)

    def close(self, discard=False) -> None:
        if self.closed:
            return
        if (
            self.ops
            and not discard
            and not messagebox.askyesno(
                "Discard edits?", "Close without saving your annotations?", parent=self.top
            )
        ):
            return
        self.closed = True
        try:
            self.top.destroy()
        except Exception:
            pass
        if self.on_close:
            self.on_close()
