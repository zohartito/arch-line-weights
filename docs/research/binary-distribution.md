# Binary Distribution Notes

This file is a technical packaging note. The Day-1 public release is source /
GitHub install only; no binary package is promised here.

## Possible Future Packaging

- PyInstaller or a similar bundler could create standalone command-line
  binaries.
- macOS distribution would need code signing and notarization.
- Windows distribution would need a separate signing path and installer test
  matrix.
- Linux distribution could start with a static archive before any desktop
  package format.

## Constraints

- Packaged binaries must keep the same MIT core license notice.
- Packaging must not hide that Illustrator is required for `apply-jsx`.
- Packaging must preserve clear errors for missing `/NumBlock` in
  `apply-saas --poche`.
- Any binary path must be verified independently from the current editable
  source install.

## Current Decision

Do not advertise binary downloads for v1. Keep public install instructions to
source/GitHub until packaging is built, signed, and tested.
