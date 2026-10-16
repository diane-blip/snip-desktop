"""Neutral native UI tokens; image content is never recolored."""

SURFACE = "#171717"
ROW = "#252525"
HOVER = "#333333"
EDGE = "#4B4B4B"
TEXT = "#F5F5F5"
MUTED = "#B8B8B8"
ACCENT = "#E8DBBE"
ACTION = "#AD8326"
ACTION_HOVER = "#8A6820"
ACTION_TEXT = "#FFFFFF"  # Approved brand pairing; not an AA small-text contrast claim.
SELECTED = "#E8E8E8"
MARKUP = "#404040"
IDLE = "#777777"
BUSY = ACTION


def button_style(primary=False):
    return dict(
        bg=ACTION if primary else ROW,
        fg=ACTION_TEXT if primary else TEXT,
        activebackground=ACTION_HOVER if primary else HOVER,
        activeforeground=ACTION_TEXT if primary else TEXT,
        relief="flat",
        borderwidth=0,
        highlightthickness=2,
        highlightbackground=ACCENT if primary else SURFACE,
        highlightcolor=ACCENT,
        font=("Segoe UI", 10),
        padx=12,
        pady=7,
        cursor="hand2",
        takefocus=True,
    )
