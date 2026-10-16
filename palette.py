"""Keyboard-accessible capture palette with native focusable buttons."""

import ctypes
import tkinter as tk

from theme import MUTED, SURFACE, TEXT, button_style
from windows_ui import place, work_area


class Palette:
    def __init__(self, root, actions, done):
        self.done, self.finished = done, False
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg=SURFACE)
        header = tk.Frame(self.top, bg=SURFACE)
        header.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(header, text="Snip", bg=SURFACE, fg=TEXT, font=("Segoe UI", 15, "bold")).pack(
            side="left"
        )
        tk.Label(header, text="Esc closes", bg=SURFACE, fg=MUTED, font=("Segoe UI", 10)).pack(
            side="right"
        )
        area = tk.Frame(self.top, bg=SURFACE)
        area.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        canvas = tk.Canvas(area, bg=SURFACE, bd=0, highlightthickness=0)
        self.canvas = canvas
        self.rows = tk.Frame(canvas, bg=SURFACE)
        window = canvas.create_window(0, 0, anchor="nw", window=self.rows)
        canvas.pack(side="left", fill="both", expand=True)
        self.rows.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        self.buttons = []
        for key, label, callback in actions:
            button = tk.Button(
                self.rows,
                text=f"{key.upper()}   {label}",
                anchor="w",
                command=lambda cb=callback: self._finish(cb),
                **button_style(),
            )
            button.pack(fill="x", pady=3)
            self.buttons.append(button)
            for char in (key.lower(), key.upper()):
                self.top.bind(char, lambda e, k=key, cb=callback: self._key(e, k, cb))
            button.bind("<FocusIn>", lambda e, b=button: self._reveal(b))
        self.top.bind("<Down>", lambda e: self._focus(1))
        self.top.bind("<Up>", lambda e: self._focus(-1))
        self.top.bind(
            "<Return>",
            lambda e: (
                self.top.focus_get().invoke()
                if isinstance(self.top.focus_get(), tk.Button)
                else None
            ),
        )
        self.top.bind("<Escape>", lambda e: self._finish(None))
        self.top.bind("<FocusOut>", lambda e: self.top.after_idle(self._check_focus))
        self.top.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-int(e.delta / 120), "units"))
        self.top.update_idletasks()
        left, upper, right, bottom = work_area(root)
        width = min(max(350, self.rows.winfo_reqwidth() + 48), right - left - 16)
        requested = header.winfo_reqheight() + 24 + self.rows.winfo_reqheight() + 16
        height = min(requested, bottom - upper - 16)
        if height < requested:
            scrollbar = tk.Scrollbar(area, command=canvas.yview)
            scrollbar.pack(side="right", fill="y")
            canvas.configure(yscrollcommand=scrollbar.set)
        x = min(max(root.winfo_pointerx() - 20, left + 8), right - width - 8)
        y = min(max(root.winfo_pointery() - 20, upper + 8), bottom - height - 8)
        place(self.top, width, height, x, y)
        self.top.focus_force()
        self.buttons[0].focus_set()

    def _check_focus(self):
        if self.finished:
            return
        focused = self.top.focus_displayof()
        if focused is None or focused.winfo_toplevel() != self.top:
            self._finish(None)

    def _focus(self, step):
        focused = self.top.focus_get()
        index = self.buttons.index(focused) if focused in self.buttons else 0
        self.buttons[(index + step) % len(self.buttons)].focus_set()
        return "break"

    def _reveal(self, button):
        self.canvas.update_idletasks()
        top = self.canvas.canvasy(0)
        if (
            button.winfo_y() < top
            or button.winfo_y() + button.winfo_height() > top + self.canvas.winfo_height()
        ):
            self.canvas.yview_moveto(button.winfo_y() / max(1, self.rows.winfo_height()))

    def _key(self, event, key, callback):
        code = ord(key.upper())
        if event.keycode == code and ctypes.windll.user32.GetAsyncKeyState(code) & 0x8000:
            self._finish(callback)

    def _finish(self, callback):
        if self.finished:
            return
        self.finished = True
        self.top.destroy()
        self.done(callback)
