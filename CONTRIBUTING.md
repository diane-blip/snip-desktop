# Contributing

Use Windows x64 and Python 3.12. Start with a small issue describing the bug or intended behavior. Never attach private captures, browser profiles, cookies or raw logs containing personal paths.

```powershell
py -3.12 -m venv .venv
.\setup-machine.ps1
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-dev.txt
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\pip-audit.exe --require-hashes -r requirements.lock
```

The default suite uses local HTTP fixtures and headless Chromium. Win32 shortcut tests reserve **Ctrl+Shift+F24**, never the production shortcut. Interactive desktop tests are opt-in:

```powershell
$env:SNIP_INTERACTIVE = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:SNIP_INTERACTIVE
```

Run interactive tests on a desktop you control. Their disposable windows briefly take focus; the scrolling fixture moves the pointer and sends wheel input only while its own window is foreground. They do not replace the clipboard or start another production shortcut.

## Code boundaries

`capture.App` owns application state on Tk's thread. Tray and hotkey callbacks only enqueue actions. Workers receive copied configuration and enqueue completion; they never touch widgets. A menu, selector, editor, scrolling job or capture browser occupies one session. Keep that ownership model when adding features.

| Module | Responsibility |
| --- | --- |
| `capture.py` | Lifecycle, queue, tray, session ownership |
| `hotkey.py` | Windows shortcut registration and release |
| `grab.py`, `region.py` | Physical screen pixels and frozen-frame selection |
| `scroll.py` | Visible-region scrolling and overlap matching |
| `active_browser.py`, `webpage.py` | Read-only URL lookup and isolated browser capture |
| `annotate.py` | Image operations and non-destructive editor |
| `save.py`, `clip.py` | Atomic file writes and clipboard transfer |
| `settings.py` | Configuration merge, validation and path resolution |
| `theme.py`, `windows_ui.py` | Shared visual tokens and Windows placement |

Keep dependencies purposeful and interfaces small. Add tests for changed behavior and failure paths, especially file preservation, cancellation, thread ownership and resource cleanup. Do not add telemetry, automatic startup, global keyboard hooks, implicit clipboard reads or shared browser profiles. Errors must identify recovery without exposing captured content or URLs in logs.

Keep the neutral visual system in [DESIGN.md](DESIGN.md). Changes must remain keyboard reachable and fit a constrained desktop work area. Record tested platforms honestly; this project does not claim macOS or Linux support.

## Dependency changes

Edit `requirements.txt`, then regenerate the runtime lock on Windows x64 with Python 3.12:

```powershell
.\.venv\Scripts\uv.exe pip compile requirements.txt --generate-hashes --no-header -o requirements.lock
```

Development inputs are in `requirements-dev.in`; regenerate `requirements-dev.txt` the same way. Review transitive changes, reinstall with `--require-hashes`, rerun checks, and reinstall Chromium through `setup-machine.ps1` when Playwright changes. Browser versions follow Playwright; browser binaries are kept inside this installation's virtual environment.

Pull requests should state the problem, resulting behavior and tests performed. Screenshots must contain fictional or intentionally public content. See [release procedure](docs/releasing.md).
