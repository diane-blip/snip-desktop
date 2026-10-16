"""Explicit URL entry. Never reads or replaces the clipboard automatically."""

import tkinter as tk

from active_browser import normalize_url
from theme import ACCENT, MUTED, ROW, SURFACE, TEXT, button_style
from windows_ui import work_area


class URLPrompt:
    def __init__(self, root):
        self.result = None
        self.top = tk.Toplevel(root)
        self.top.title("Capture a web page")
        self.top.configure(bg=SURFACE, padx=16, pady=16)
        self.top.attributes("-topmost", True)
        tk.Label(
            self.top, text="Web page URL", bg=SURFACE, fg=TEXT, font=("Segoe UI", 13, "bold")
        ).pack(anchor="w")
        tk.Label(
            self.top,
            text="Use the complete http:// or https:// address.",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 12))
        self.entry = tk.Entry(
            self.top,
            bg=ROW,
            fg=TEXT,
            insertbackground=TEXT,
            highlightthickness=2,
            highlightcolor=ACCENT,
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.entry.pack(fill="x", ipady=7)
        self.error = tk.Label(
            self.top, text="", bg=SURFACE, fg=TEXT, font=("Segoe UI", 10), anchor="w"
        )
        self.error.pack(fill="x", pady=(5, 12))
        buttons = tk.Frame(self.top, bg=SURFACE)
        buttons.pack(anchor="e")
        self.cancel_button = tk.Button(buttons, text="Cancel", command=self.close, **button_style())
        self.cancel_button.pack(side="left", padx=(0, 8))
        self.capture_button = tk.Button(
            buttons, text="Capture", command=self.accept, **button_style(True)
        )
        self.capture_button.pack(side="left")
        self.top.bind("<Escape>", lambda e: self.close())
        self.entry.bind("<Return>", lambda e: self.accept())
        self.cancel_button.bind("<Return>", lambda e: self.close())
        self.capture_button.bind("<Return>", lambda e: self.accept())
        left, upper, right, bottom = work_area(root)
        self.top.geometry(f"{min(560, right - left - 32)}x240")
        self.entry.focus_force()
        self.top.grab_set()

    def accept(self):
        url = normalize_url(self.entry.get())
        if not url:
            self.error.configure(text="Enter a valid web address without embedded login details.")
            return
        self.result = url
        self.close()

    def close(self):
        self.top.grab_release()
        self.top.destroy()

    def show(self):
        self.top.wait_window()
        return self.result
