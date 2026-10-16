# Snip

Windows desktop utility for capturing regions, the desktop, a window, scrolling content or a web page; annotating a saved capture; and saving PNGs with optional clipboard copy.

Preserve the installed tool's two entry points: Ctrl+Shift+S and its tray menu. One capture or editor session runs at a time. Every successful capture is saved before clipboard copy. Cancellation and failure leave existing files intact. Setup does not enable startup or replace another installation.

The public edition uses neutral dark grays, white text and restrained teal/blue. Native system typography, visible keyboard focus and clear errors take priority over decorative branding. The palette, region overlay, URL prompt and annotation editor share these colors. The image being edited retains its own colors.

The repository is Windows/Python source with setup scripts. It needs no service account or API key. Web capture uses a separate local Chromium profile and visits user-selected URLs. Local captures and browser sessions are private runtime data, excluded from Git and releases.

The installed private edition remains unchanged. The public source has separate release history and versioned downloads.
