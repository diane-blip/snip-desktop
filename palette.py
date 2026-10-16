"""Pop-up capture palette: one hotkey opens it, every action is one letter
(or a click) away.

Rendered entirely on a canvas so it gets true rounded corners (via the
-transparentcolor trick), DPI-aware sizing, and soft layered surfaces instead
of the stock flat-widget look. SRC tokens: gold does the structural eyebrow,
pink only marks the interactive key chips.
"""
import ctypes
import tkinter as tk
import tkinter.font as tkfont

INK = "#161314"        # container surface
ROW = "#211d1e"        # row surface
HOVER = "#2d2728"      # row hover
EDGE = "#39322f"       # hairline container border
PAPER = "#FEFCFD"
MUTED = "#8d8586"
PINK = "#F0BDCE"  # softened from brand #F49CBB (lighter, desaturated) at Di's request
GOLD = "#AD8326"
TRANSPARENT = "#010203"  # never-drawn key color -> real rounded corners


def _round_rect(c: tk.Canvas, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def _pick_font(root, preferred, fallback="Segoe UI"):
    try:
        families = set(tkfont.families(root))
        for name in preferred:
            if name in families:
                return name
    except Exception:
        pass
    return fallback


class Palette:
    """actions = [(key, label, callback), ...]; done(callback|None) is called
    exactly once when a choice is made or the palette is dismissed."""

    def __init__(self, root: tk.Tk, actions, done):
        self.done = done
        self.finished = False

        try:
            s = ctypes.windll.user32.GetDpiForSystem() / 96.0
        except Exception:
            s = 1.0
        text_family = _pick_font(root, ["Segoe UI Variable Text", "Segoe UI"])
        disp_family = _pick_font(root, ["Segoe UI Variable Display", "Segoe UI"])

        pad = int(16 * s)
        row_h = int(44 * s)
        row_gap = int(5 * s)
        head_h = int(26 * s)
        chip = int(27 * s)
        width = int(304 * s)
        height = pad * 2 + head_h + len(actions) * (row_h + row_gap) - row_gap

        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg=TRANSPARENT)
        self.top.attributes("-transparentcolor", TRANSPARENT)

        c = tk.Canvas(self.top, width=width, height=height,
                      bg=TRANSPARENT, highlightthickness=0, bd=0)
        c.pack()
        self.canvas = c

        # Container: soft rounded surface with a hairline edge
        _round_rect(c, 1, 1, width - 1, height - 1, int(20 * s),
                    fill=INK, outline=EDGE, width=max(1, int(s)))

        # Header: gold eyebrow + muted dismiss hint
        eyebrow = " ".join("SNIP")  # wide-tracked, SRC eyebrow style
        c.create_text(pad + int(2 * s), pad + head_h // 2 - int(3 * s),
                      anchor="w", text=eyebrow, fill=GOLD,
                      font=(disp_family, -int(11 * s), "bold"))
        c.create_text(width - pad - int(2 * s), pad + head_h // 2 - int(3 * s),
                      anchor="e", text="esc", fill=MUTED,
                      font=(text_family, -int(11 * s)))

        # Rows
        self._row_rects = {}
        y = pad + head_h
        for i, (key, label, cb) in enumerate(actions):
            tag = f"row{i}"
            rect = _round_rect(c, pad, y, width - pad, y + row_h, int(12 * s),
                               fill=ROW, outline="", tags=tag)
            self._row_rects[tag] = rect
            cy = y + row_h // 2
            cx = pad + int(12 * s)
            _round_rect(c, cx, cy - chip // 2, cx + chip, cy + chip // 2,
                        chip // 2, fill=PINK, outline="", tags=tag)
            c.create_text(cx + chip // 2, cy - int(1 * s), text=key.upper(),
                          fill=INK, font=(disp_family, -int(13 * s), "bold"),
                          tags=tag)
            c.create_text(cx + chip + int(13 * s), cy - int(1 * s), anchor="w",
                          text=label, fill=PAPER,
                          font=(text_family, -int(14 * s)), tags=tag)

            c.tag_bind(tag, "<Enter>", lambda e, t=tag: self._hover(t, True))
            c.tag_bind(tag, "<Leave>", lambda e, t=tag: self._hover(t, False))
            c.tag_bind(tag, "<ButtonRelease-1>", lambda e, x=cb: self._finish(x))
            y += row_h + row_gap

        self.top.bind("<Escape>", lambda e: self._finish(None))
        self.top.bind("<FocusOut>", lambda e: self._finish(None))
        for key, _label, cb in actions:
            self.top.bind(key.lower(), lambda e, x=cb: self._finish(x))
            self.top.bind(key.upper(), lambda e, x=cb: self._finish(x))

        # Place near the cursor, clamped to the screen
        x = min(max(root.winfo_pointerx() - int(20 * s), 8),
                root.winfo_screenwidth() - width - 8)
        yy = min(max(root.winfo_pointery() - int(20 * s), 8),
                 root.winfo_screenheight() - height - 8)
        self.top.geometry(f"{width}x{height}+{x}+{yy}")
        self.top.focus_force()

    def _hover(self, tag, on):
        self.canvas.itemconfigure(self._row_rects[tag], fill=HOVER if on else ROW)
        self.canvas.configure(cursor="hand2" if on else "")

    def _finish(self, cb):
        if self.finished:
            return
        self.finished = True
        try:
            self.top.destroy()
        except Exception:
            pass
        self.done(cb)
