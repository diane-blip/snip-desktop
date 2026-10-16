"""Neutral native UI tokens; image content is never recolored."""

SURFACE = "#181B1E"
ROW = "#24292E"
HOVER = "#323A41"
EDGE = "#4B555E"
TEXT = "#F5F7F8"
MUTED = "#B3BDC5"
ACCENT = "#90D5CF"
MARKUP = "#2563A6"
IDLE = "#66717A"
BUSY = "#0F766E"


def button_style(primary=False):
    return dict(
        bg=ACCENT if primary else ROW,
        fg=SURFACE if primary else TEXT,
        activebackground=HOVER,
        activeforeground=TEXT,
        relief="flat",
        borderwidth=0,
        highlightthickness=2,
        highlightbackground=SURFACE,
        highlightcolor=ACCENT,
        font=("Segoe UI", 10),
        padx=12,
        pady=7,
        cursor="hand2",
        takefocus=True,
    )
