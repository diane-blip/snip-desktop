# Snip

A Windows tray tool for screenshots, scrolling captures and full web pages. Save a PNG, copy it to the clipboard, and add arrows, boxes, blur or opaque redaction.

**[Download Snip 0.1.1](https://github.com/diane-blip/snip-desktop/releases/tag/v0.1.1)** · Windows x64 · Python 3.12 · MIT license

This is a source release with a setup script. It requires Python and downloads its dependencies and a separate Chromium browser. There is no standalone executable or macOS build.

![Snip's native capture menu](docs/images/menu.png)

## Install

1. Install **64-bit Python 3.12** from [python.org](https://www.python.org/downloads/windows/), including the Python launcher and Tcl/Tk.
2. Download `Snip-0.1.1-source.zip` and `SHA256SUMS.txt` from the release. Check the ZIP's SHA-256 against the published file:

   ```powershell
   Get-FileHash .\Snip-0.1.1-source.zip -Algorithm SHA256
   ```

3. Extract the ZIP to a permanent, writable folder. Open PowerShell in the extracted `Snip-0.1.1` folder and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-machine.ps1
   .\.venv\Scripts\python.exe capture.py
   ```

The execution-policy override applies only to that installer process. Setup creates `.venv`, installs hash-locked packages and downloads Chromium inside that environment. It does not start the app, change an existing installation or add startup shortcuts. Expect several hundred MB of downloads and allow roughly 1 GB of free disk space.

To run without a console after the first successful start:

```powershell
Start-Process -WindowStyle Hidden -FilePath .\.venv\Scripts\pythonw.exe -ArgumentList 'capture.py' -WorkingDirectory (Get-Location).Path
```

Only one Snip instance can run. An older installed copy also holds this lock; keep using it or quit it deliberately before starting another edition. Installing the public release never stops it for you.

## Capture

Press **Ctrl+Shift+S** or open **Snip menu** from the tray. Use the letter shown, click an action, or move focus with Tab/arrow keys and press Enter. Esc closes the menu.

| Key | Action | Behavior |
| --- | --- | --- |
| S | Snip a region | Drag a rectangle on a frozen desktop image. Esc or right-click cancels. |
| F | Full screen | Capture the entire virtual desktop, including all monitors. |
| A | Active window | Capture visible pixels of the window selected before opening the menu. |
| D | Scrolling capture | Select the scrollable content area. Snip scrolls and joins overlapping frames. |
| U | Full web page | Read the selected browser's URL when available; otherwise ask for the address. |
| E | Annotate last capture | Open the last capture, or the newest PNG in the capture folder after a restart. |
| O | Open captures folder | Open the destination in Explorer. |

Captures save to `~/Pictures/Snip` by default. A successful save happens before clipboard copy. If the clipboard is busy or the image is too tall, the PNG is still kept. One capture or editor session runs at a time; finish or close it before starting another action or quitting.

### Scrolling captures

Choose only the scrollable content, excluding fixed headers, sidebars and scrollbars. The selected application must stay in front. Press **Esc**, move the pointer or switch windows to stop; Snip saves the portion captured so far. Captures also stop at the bottom, configured limits or unreliable alignment. Check the result before sharing: animation, repeated blank regions and sticky content can prevent a complete stitch. Reduce `scroll.wheel_ticks` if it stops too early.

### Web pages and sign-in

Web captures render in Snip's separate Chromium browser, so they can differ from the page in your everyday browser. URL lookup uses Windows accessibility APIs without touching the clipboard. If the address is unavailable, paste or type it in the prompt. **Capture web address…** in the tray always opens that prompt.

For pages requiring sign-in, choose **Open capture browser**, sign in there, then close every capture-browser window before capturing. Sessions stay in this installation's `browser-profile/`. Sites can reject automated browsing. HTTP errors, timeouts and oversized pages produce no final PNG; use a region or scrolling capture when full-page capture cannot finish.

### Annotate

Choose Arrow, Box, Blur or Redact, then drag on the image. **Undo** or **Ctrl+Z** removes the last operation. **Save + copy** or **Ctrl+S** creates a new PNG; when clipboard copy is disabled, the button reads **Save PNG**. Scroll to reach a tall or wide image. Esc or closing the editor asks before discarding edits.

**Redact covers the selected pixels with solid black in the exported PNG. Blur only softens them.** The original image stays on disk. Inspect the export, and share that file rather than the original. See [privacy and redaction boundaries](SECURITY.md).

## Settings, startup and removal

Choose **Open config** in the tray to edit `config.local.toml`; **Reload config** applies valid settings while idle. See [all settings and limits](docs/configuration.md).

Optional desktop and sign-in shortcuts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-startup.ps1
```

Remove this installation's shortcuts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-startup.ps1 -Remove
```

The script owns `Snip Desktop.lnk`. It refuses to replace a shortcut belonging to another installation and does not touch older `Capture.lnk` shortcuts. To uninstall, remove these shortcuts, quit Snip, then delete its installation folder. Your captures remain in their save folder. Removing the installation folder deletes its separate browser sessions; it does not clear Windows clipboard history.

For an update, keep the old folder until the new release works. Install the new ZIP separately, copy only your intended `config.local.toml` overrides, and quit the old app before starting the new one. Re-create optional shortcuts after removing the old installation's owned shortcuts. Do not copy `.venv` or publish a browser profile.

## Troubleshooting and limits

- **Shortcut unavailable:** another app owns Ctrl+Shift+S. Use Snip's tray menu or resolve that conflict in the other app. Snip does not intercept all keyboard input.
- **No visible window at startup:** Snip lives in the tray, sometimes under Windows' hidden-icons arrow. Run the console command above to see startup errors; check `capture.log` and local configuration.
- **Browser missing:** rerun `setup-machine.ps1` in this installation. Its private Chromium must match its Playwright version.
- **No notification:** Windows can hide tray notifications. Check the capture folder; notifications are not the file itself.
- **Black/protected content:** secure desktop, DRM surfaces, minimized windows and some GPU-rendered content cannot be captured reliably. Snip captures visible pixels and does not bypass protection.
- **Displays:** negative desktop origins are supported. Mixed-DPI multi-monitor hardware and screen-reader operation have not been fully verified. This release targets Windows x64 with Python 3.12; Windows 11 is the locally tested desktop.

[Development and architecture](CONTRIBUTING.md) · [Verification](docs/verification.md) · [Changelog](CHANGELOG.md) · [Credits](AUTHORS.md) · [License](LICENSE)
