# Configuration

Put overrides in `config.local.toml` beside `capture.py`. Leave `config.toml` as the release defaults. From the tray, choose **Open config**, edit, save, then **Reload config** while Snip is idle. An invalid reload keeps the previous settings.

```toml
save_dir = '~/Pictures/Snip'
copy_to_clipboard = true
clipboard_max_height = 8000
max_pixels = 40000000
sounds = true

[scroll]
wheel_ticks = 4
settle_ms = 450
max_height = 20000
max_steps = 80

[fullpage]
viewport_width = 1440
timeout_seconds = 60
settle_ms = 1500
max_height = 20000
```

Only include settings you want to change. In TOML, put top-level settings before a table such as `[scroll]`. Single-quoted Windows paths, such as `'D:\Captures'`, preserve backslashes. Relative paths resolve from the app folder. `~` resolves to your home directory. The save folder is created on the first save.

| Setting | Accepted values | Effect |
| --- | --- | --- |
| `save_dir` | Nonempty path | Destination for PNG files |
| `copy_to_clipboard` | `true` / `false` | Copy captures and annotated exports after saving |
| `clipboard_max_height` | 100–20,000 | Taller images are saved without clipboard copy |
| `max_pixels` | 1,000,000–80,000,000 | Limits capture and annotation image size |
| `sounds` | `true` / `false` | Play a quiet confirmation after capture |
| `scroll.wheel_ticks` | 1–10 | Wheel distance between frames; reduce if stitching stops early |
| `scroll.settle_ms` | 100–3,000 | Wait after each wheel movement |
| `scroll.max_height` | 500–30,000 | Stop at this image height |
| `scroll.max_steps` | 1–120 | Maximum wheel movements |
| `fullpage.viewport_width` | 320–3,840 | Capture browser width in CSS pixels |
| `fullpage.timeout_seconds` | 5–120 | Budget for navigation and capture; browser cleanup may add time |
| `fullpage.settle_ms` | 0–5,000 | Final wait before capture |
| `fullpage.max_height` | 900–30,000 | Oversized web pages fail without exporting a partial image |

Unknown keys, wrong types and out-of-range values are rejected. The pixel limit can further reduce the permitted scrolling height. These limits bound image dimensions; they are not a strict process-memory quota.

The public app's browser profile is always `browser-profile/` inside this installation. There is no option to attach your ordinary browser profile.
