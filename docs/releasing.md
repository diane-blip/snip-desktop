# Releasing Snip

1. Work from clean GitHub `main`. Update the version in `pyproject.toml`, changelog and user-facing download links together.
2. Run the checks in [CONTRIBUTING.md](../CONTRIBUTING.md), including the opt-in Windows desktop fixtures. Review the rendered palette, URL/error prompt, selector and editor with fictional content at normal and constrained sizes. Preserve any existing installation during tests.
3. Check installation and optional shortcut creation/removal in a separate folder. Confirm a foreign shortcut cannot be replaced or removed.
4. Run a current secret scanner against the entire public history and the exact exported tree. Inspect the file list for runtime data, private profiles, local configuration, logs and unrelated content. Dependency audits are required but do not replace review.
5. Commit and push; wait for the Windows checks on that exact SHA. Create the version tag from that commit. Do not release a different or uncommitted tree.
6. Export tracked files with `git archive --format=zip --prefix=Snip-<version>/ --output=dist/Snip-<version>-source.zip <tag>`. The archive contains source and setup scripts, not a signed executable. Generate `SHA256SUMS.txt` from those exact bytes.
7. Extract the archive in a fresh folder. Run the documented installer, dependency check and tests there. Do not copy an existing virtual environment or browser profile into the test installation.
8. Upload the source ZIP and checksum file to a GitHub release. Download both through an unauthenticated connection, compare SHA-256, inspect the archive and confirm the release tag equals `main`.
9. Record the release date, version, checks, platform and unverified boundaries in [verification.md](verification.md). Confirm the local checkout is clean and matches GitHub.

Keep release notes factual. Do not call a source archive a standalone installer, claim macOS support, or describe tests as a guarantee of correctness. Publish no capture from a real private desktop in release documentation.
