# Security and privacy

Report a vulnerability through [GitHub private vulnerability reporting](https://github.com/dianewhiddon/snip-desktop/security/advisories/new). Do not put sensitive examples in a public issue. Include the affected version, a minimal fictional reproduction and expected impact. Security fixes target the latest release; no response-time guarantee is offered.

## Data handling

- Captures are local PNG files. Snip has no analytics, account service or upload endpoint.
- Capturing a web page visits that URL in a separate Chromium browser. The site and its third parties can observe those requests. Setup downloads packages and Chromium.
- **Open capture browser** lets you sign in inside Snip's separate profile. Cookies and sessions persist in `browser-profile/`; treat that directory as sensitive. Snip does not read your everyday browser's cookies or profile.
- Browser-address lookup uses Windows accessibility APIs. It does not send copy/paste keystrokes or read/write the clipboard. If lookup fails, enter the URL explicitly.
- Successful captures replace the Windows clipboard by default. Set `copy_to_clipboard = false` to disable this. Clipboard history and synchronization are controlled by Windows, not Snip.
- Application logs record event/error types, not capture contents or web addresses. The current log and two backups are bounded to about 1 MB each. Local paths and file names may still appear in operating-system diagnostics.
- Filenames contain a capture kind, timestamp and random suffix. They do not include page titles or URLs.

## Redaction

**Redact** replaces the selected pixels with opaque black pixels in the exported PNG. **Blur is not redaction**; blurred content can remain readable or recoverable. Inspect the saved export before sharing. The original capture remains unchanged on disk and may remain in clipboard history or backups. Redacting an export does not erase those copies.

## Boundaries

Screen capture can include private content visible on any monitor. Scrolling capture sends wheel input to the selected visible area; moving the pointer, pressing Esc or changing the foreground window stops it. The resulting image can contain only the portion captured before stopping.

The app does not bypass protected content, Windows secure desktop, browser authentication, website access controls or operating-system permissions. Do not run it as administrator. Browser capture uses Chromium's default sandbox; do not add `--no-sandbox`.

Runtime data, `.venv`, local configuration, logs and development review captures are excluded from the repository and release archive. Release checks include dependency advisories and secret scanning; neither proves that software is free of vulnerabilities.
