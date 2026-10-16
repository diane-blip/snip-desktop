# Capture

Screen capture for Windows. Ctrl+Shift+S opens the Snip menu; every capture lands as a PNG in `Pictures\Captures` AND on the clipboard, with a toast confirming.

Lives at `projects/capture/` in the vault (gitignored, own repo `diane-blip/capture`). Vault card: `projects/capture.md`.

## Open the menu with Ctrl+Shift+S

Press **Ctrl+Shift+S** or left-click the Snip tray icon to open the **capture menu**. Choose an action with a click or its letter while the menu is open:

| Letter | Action |
|---|---|
| **S** | Snip a region — screen freezes and darkens, drag a rectangle. Esc or right-click cancels. |
| **F** | Full screen (all monitors) |
| **A** | The active window |
| **D** | Scrolling capture — select the scrolling area, then hands off: the app scrolls it and stitches one tall image. Esc stops early (keeps what it has). |
| **U** | Entire web page, top to bottom (the GoFullPage replacement) |
| **E** | Annotate the last capture — arrows, boxes, blur |
| **O** | Open the captures folder |

**Ctrl+Shift+S is the only global Snip shortcut.** Windows owns this registration, which is released on quit; a conflict is reported rather than stolen. No blocking keyboard hook is installed. The old Ctrl+Shift+F/A/U/D/E bindings remain removed. Ctrl+Shift+S belongs to Snip while running; other shortcuts remain available to their foreground apps.

Full-page capture reads the address from the active Chrome, Edge, Brave, or Firefox tab. Open the page and choose **Full web page**; there is nothing to copy or type. The tray menu's **Snip full page…** item keeps a manual URL box as a fallback when you deliberately want to capture a page that is not open.

## Scrolling capture

For anything scrollable that isn't a URL — a PDF, a long Obsidian note, Slack, an email thread. Select just the area that scrolls (leave out fixed headers/sidebars), then don't touch the mouse or keyboard: the app scrolls the area itself, watches how far the content moves, and stitches only the new rows into one tall PNG. It stops on its own at the bottom, or press Esc to stop early and keep what it has.

Tips: select only the scrolling content, not the whole window. Content that animates while scrolling, or large stretches of completely blank space, can confuse the stitcher and end the capture early — scroll captures of mostly-blank areas are its known weak spot.

## Annotating

Opens your most recent capture in a small dark editor: **Arrow**, **Box** (both brand pink), and **Blur** (drag over anything you want unreadable). Ctrl+Z undoes. "Save + copy" writes `<name>-annotated.png` next to the original and puts it on your clipboard — the original stays untouched. Also available from the tray menu.

## Logged-in pages

The full-page browser keeps its own profile, separate from Chrome. For a page behind a login (client dashboards, Cloudflare, Kit):

1. Tray icon → **"Open capture browser (log in to sites)"**
2. Log into the site in the window that opens, then close it.
3. Capture the URL as usual — it's logged in from now on.

## Setup (per machine)

Run `setup-machine.ps1`. It creates the local environment if needed, installs
the pinned dependencies and matching Chromium engine, and adds Capture to
Windows startup. Rerun it after pulling an update if Full Page reports that its
browser executable is missing.

No API keys needed. Run it: double-click `start-capture.vbs` (silent) or `.venv\Scripts\python.exe capture.py` (with console, for debugging).

Start with Windows is included in `setup-machine.ps1`; `setup-startup.ps1` can
still repair only the shortcut.

## Config

`config.toml` — save folder, clipboard behavior, full-page viewport width and timeouts. Tray menu has "Reload config".

## Known limitations

- Scrolling capture assumes vertical scrolling and static content; animated GIFs/videos in the selected area, sticky elements inside the selection, or long blank stretches can end it early or leave a visible seam. For web pages use Full web page in the Snip menu.
- Very tall PNGs (over `clipboard_max_height`, default 8000px) are saved to file but not copied to the clipboard, so pasting stays fast.
- Mixed-DPI multi-monitor setups (e.g. a scaled laptop plus an unscaled external) may offset the snip overlay; single displays and matched scaling are fine.
- Sites with aggressive bot protection may show a challenge page to the capture browser; log in via "Open capture browser" first, which usually clears it.
