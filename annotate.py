"""Minimal dark annotation editor: arrows, boxes, blur.

Opens the chosen capture, lets Di drag arrows/boxes (brand pink) or blur
regions, then saves alongside as <name>-annotated.png + clipboard. All edits
are kept as an op list over the original image, so Undo is exact.
"""
import math
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageTk

PINK = "#F49CBB"  # markup stays full-strength brand pink so it pops on light captures
INK = "#111111"
PANEL = "#221f20"
PAPER = "#FEFCFD"
BLUR_RADIUS = 14


def render(base: Image.Image, ops: list) -> Image.Image:
    img = base.copy()
    draw = ImageDraw.Draw(img)
    w = max(4, base.width // 400)  # stroke width scales with image size
    for kind, x0, y0, x1, y1 in ops:
        if kind == "blur":
            box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            if box[2] - box[0] > 2 and box[3] - box[1] > 2:
                img.paste(img.crop(box).filter(ImageFilter.GaussianBlur(BLUR_RADIUS)), box)
                draw = ImageDraw.Draw(img)
        elif kind == "box":
            draw.rectangle((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)),
                           outline=PINK, width=w)
        elif kind == "arrow":
            draw.line((x0, y0, x1, y1), fill=PINK, width=w)
            ang = math.atan2(y1 - y0, x1 - x0)
            head = w * 4.5
            for spread in (math.radians(155), math.radians(-155)):
                draw.line((x1, y1,
                           x1 + head * math.cos(ang + spread),
                           y1 + head * math.sin(ang + spread)),
                          fill=PINK, width=w)
    return img


class Annotator:
    def __init__(self, root: tk.Tk, path: Path, notify, on_close=None):
        self.path = path
        self.notify = notify
        self.on_close = on_close
        self.base = Image.open(path).convert("RGB")
        self.ops: list = []
        self.tool = "arrow"
        self.start = None
        self.preview_id = None
        self.tool_buttons = {}

        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        self.scale = min(1.0, (screen_w * 0.85) / self.base.width,
                         (screen_h * 4.0) / self.base.height)  # cap width, allow tall
        self.disp_w = int(self.base.width * self.scale)
        self.disp_h = int(self.base.height * self.scale)

        self.top = tk.Toplevel(root)
        self.top.title(f"Annotate — {path.name}")
        self.top.configure(bg=INK)
        view_h = min(int(screen_h * 0.82), self.disp_h)
        self.top.geometry(f"{self.disp_w + 20}x{view_h + 64}")

        bar = tk.Frame(self.top, bg=INK)
        bar.pack(fill="x", padx=10, pady=8)
        for name, label in (("arrow", "Arrow"), ("box", "Box"), ("blur", "Blur")):
            b = tk.Button(bar, text=label, relief="flat", padx=12, pady=3,
                          command=lambda n=name: self.set_tool(n))
            b.pack(side="left", padx=(0, 6))
            self.tool_buttons[name] = b
        tk.Button(bar, text="Undo", relief="flat", padx=12, pady=3, bg=PANEL, fg=PAPER,
                  command=self.undo).pack(side="left", padx=(12, 0))
        tk.Button(bar, text="Save + copy", relief="flat", padx=14, pady=3,
                  bg=PINK, fg=INK, font=("Segoe UI", 10, "bold"),
                  command=self.save).pack(side="right")
        self.set_tool("arrow")

        frame = tk.Frame(self.top, bg=INK)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.canvas = tk.Canvas(frame, width=self.disp_w, height=view_h,
                                bg=INK, highlightthickness=0,
                                scrollregion=(0, 0, self.disp_w, self.disp_h))
        vbar = tk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.photo = None
        self.img_id = self.canvas.create_image(0, 0, anchor="nw")
        self.refresh()

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-e.delta // 120, "units"))
        self.top.bind("<Control-z>", lambda e: self.undo())
        self.top.bind("<Escape>", lambda e: self.close())
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.top.focus_force()

    # -- tools / render ---------------------------------------------------------

    def set_tool(self, name: str) -> None:
        self.tool = name
        for n, b in self.tool_buttons.items():
            b.configure(bg=PINK if n == name else PANEL, fg=INK if n == name else PAPER)

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
        return self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)

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
            self.preview_id = self.canvas.create_line(x0, y0, x1, y1, fill=PINK,
                                                      width=3, arrow=tk.LAST,
                                                      arrowshape=(14, 18, 6))
        else:
            dash = (5, 3) if self.tool == "blur" else None
            self.preview_id = self.canvas.create_rectangle(x0, y0, x1, y1,
                                                           outline=PINK, width=2, dash=dash)

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
        out = (self.path if self.path.stem.endswith("-annotated")
               else self.path.with_name(self.path.stem + "-annotated.png"))
        img = render(self.base, self.ops)
        img.save(out, "PNG")
        try:
            clip.copy_image(img)
            note = " · on clipboard"
        except Exception:
            note = ""
        self.notify(f"{out.name}{note}")
        self.close()

    def close(self) -> None:
        try:
            self.top.destroy()
        except Exception:
            pass
        if self.on_close:
            self.on_close()
