# Release verification

## 0.1.1 · October 16, 2026

27 default tests and all nine controlled native desktop checks passed. The runtime lock passed its advisory audit. Capture, save, clipboard and installer behavior are unchanged.

The implemented gold theme was compared with the approved native previews at normal and constrained sizes, including populated, empty, hover, focus and error states where applicable. Actions are gold with white labels; links and dark-surface focus are light gold; surfaces and selections are neutral gray. White on gold is an approved visual exception, not a claim of AA small-text contrast. Full screen-reader, high-contrast and mixed-DPI support remain unverified.

Release assets are built from the exact commit, with hosted checks, exported-tree/history secret scans and an unauthenticated SHA-256 download check recorded in the versioned release notes. Existing personal installations are not modified.

## Previous release evidence


## 0.1.0

Local verification: October 15, 2026, Windows 11 x64, Python 3.12.

- **36 tests passed**, including nine opt-in desktop tests. These cover actual window pixels, scrolling pixels against an exact fixture, frozen-frame region selection/cancellation, negative-coordinate placement, keyboard operation, tray startup/shutdown and a live browser-address lookup that leaves the clipboard sequence unchanged.
- The production shortcut was not registered during tests. A separate Ctrl+Shift+F24 registration exercised Windows conflict detection, message delivery and release.
- Real headless Chromium captured a local 2,700-pixel page. HTTP failure and an oversized page produced no final file.
- Regression tests cover atomic saves, collision protection, source preservation, opaque redaction, invalid configuration, clipboard failure and worker completion through Tk's queue.
- Ruff lint and format checks passed. Installed dependencies passed `pip check`; the runtime lock had no known advisories in the release-time `pip-audit` result.
- Optional shortcut creation/removal and refusal to remove a foreign shortcut passed in an isolated directory.
- An independent Impeccable review inspected eight native interface captures. Its two material findings, image access in a narrow editor and focused Cancel behavior, were fixed and scored resolved in the follow-up review.

GitHub's [Checks workflow](https://github.com/diane-blip/snip-desktop/actions) installs the released environment on Windows, runs the default suite and audits dependencies. Nine desktop fixtures are deliberately skipped there; local interactive evidence is separate from hosted CI.

The release process also requires a fresh archive installation, full public-history and exported-tree secret scans, and an unauthenticated download/checksum comparison. The versioned release notes record those completed checks for the exact published artifact.

## Limits of the evidence

The desktop fixtures are controlled samples, not a claim that every application, site or display arrangement works. Mixed-DPI physical monitor combinations, full screen-reader access, localized browser address bars, Windows 10 and Windows ARM are not verified. Native clipboard pixel transfer is covered through its encoded payload and resource/failure tests; the release checks do not overwrite a user's existing clipboard for a real paste test.

Scrolling capture can end early on animation, repeated blank content or fixed elements. Website authentication and bot detection vary by site. High-contrast themes and large text scaling have not received a complete accessibility review. Windows source downloads are unsigned; there is no standalone executable in this release.
