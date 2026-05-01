# Binary distribution — PyInstaller + signing, 2026

> Sub-agent research, 2026-04-30. Roadmap Phase D depends on this:
> shipping `arch-lw` as a single signed binary so buyers don't need
> Python installed.

## Recommendation

| Decision | Choice | Annual cost |
|---|---|---|
| Bundler | **PyInstaller 6.x** | $0 |
| macOS signing | Apple Developer Program | **$99** |
| macOS notarization | `xcrun notarytool` (included with Apple Dev) | $0 |
| Windows signing | **Azure Trusted Signing** | **~$120** ($10/mo) |
| Linux | Static binary, optional Flatpak later | $0 |
| Distribution | Lemon Squeezy auto-fulfillment | Per-tx fee |
| **Year 1 fixed cost** | | **~$231** (Apple + Azure + domain) |

## Bundler comparison

| Tool | Pros | Cons | Verdict |
|---|---|---|---|
| **PyInstaller 6.x** | Mature; --onefile + --windowed flags; great hidden-imports support; works with pikepdf+pymupdf+shapely | Larger output (~80–120 MB); first-launch slow on macOS due to extraction | ✅ Use |
| Briefcase (BeeWare) | Cross-platform, native installers | Newer; doesn't support all our deps cleanly; iOS/Android focus | ❌ |
| py2app | Native macOS bundle | macOS-only; needs separate Windows path | ❌ |
| Nuitka | Compiles to C; faster startup; smaller output | Painful with C extensions (pymupdf, shapely); long build times | ❌ Reconsider for v2 |
| shiv / zipapp | Tiny output | Requires Python on user's machine | ❌ Defeats the goal |
| cx_Freeze | Solid, simple | Less docs, smaller community than PyInstaller | ❌ |

## PyInstaller spec sketch

`packaging/arch-lw.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("pikepdf", "pymupdf", "shapely", "PIL", "numpy", "click"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

a = Analysis(
    ["src/arch_line_weights/cli.py"],
    pathex=["src"],
    binaries=binaries, datas=datas,
    hiddenimports=hiddenimports + ["arch_line_weights"],
    hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=["tkinter", "pytest"],
    noarchive=False, optimize=2,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="arch-lw",
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity="Developer ID Application: Zohar Tito (TEAMID)",
    entitlements_file="packaging/entitlements.plist",
)
```

Build:

```bash
pyinstaller packaging/arch-lw.spec --clean --noconfirm
```

Expected output: `dist/arch-lw` (~95 MB on macOS, ~80 MB on Windows).

## macOS — Developer ID + notarization

### One-time setup

1. Enroll in Apple Developer Program — $99/yr at developer.apple.com.
2. Create a **Developer ID Application** certificate in the Developer
   portal; download and add to login keychain.
3. Generate an **app-specific password** at appleid.apple.com for
   `notarytool` (don't use your Apple ID password).
4. Store as repo secrets:
   - `APPLE_ID` — your Apple ID email
   - `APPLE_PASSWORD` — the app-specific password
   - `APPLE_TEAM_ID` — visible in Developer portal membership
   - `APPLE_DEVELOPER_ID_CERT` — base64 of the .p12
   - `APPLE_DEVELOPER_ID_CERT_PASSWORD` — the .p12 export password

### Per-build flow

```bash
# 1. PyInstaller signs each binary it produces with the codesign_identity
#    in the .spec; if not, sign manually:
codesign --deep --force --options runtime \
  --sign "Developer ID Application: Zohar Tito (TEAMID)" \
  --entitlements packaging/entitlements.plist \
  dist/arch-lw

# 2. Zip for notarization
ditto -c -k --keepParent dist/arch-lw arch-lw.zip

# 3. Submit to notary service (synchronous, ~2-5 min)
xcrun notarytool submit arch-lw.zip \
  --apple-id "$APPLE_ID" \
  --password "$APPLE_PASSWORD" \
  --team-id "$APPLE_TEAM_ID" \
  --wait

# 4. Staple the ticket so Gatekeeper works offline
xcrun stapler staple dist/arch-lw

# 5. Verify
spctl -a -v dist/arch-lw
```

### Entitlements (`packaging/entitlements.plist`)

For a CLI tool that reads/writes user files and runs subprocesses:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

(JIT entitlement needed because some deps lazily compile bytecode.)

## Windows — Azure Trusted Signing

**Why over EV cert?**

| | EV cert | Azure Trusted Signing |
|---|---|---|
| Annual cost | ~$300 (DigiCert/Sectigo) | ~$120 ($10/mo) |
| Hardware token | Yes (USB HSM) | No |
| Instant SmartScreen reputation | Yes | Yes (since 2024) |
| CI integration | Painful (HSM in cloud) | Native (Azure SDK) |
| Renewal | Manual every 1-3 years | Auto |

Azure Trusted Signing replaces both OV cert + SmartScreen-warming
ritual. Requires an Azure tenant, but the certificates are managed
inside Azure rather than on a USB token.

### One-time setup

1. Create Azure account (free tier OK for setup).
2. Provision a Trusted Signing account in the Azure portal.
3. Create a Certificate Profile (the identity).
4. Verify your identity (one-time, takes 1-3 days for individuals).
5. Store as GitHub secrets:
   - `AZURE_TENANT_ID`
   - `AZURE_CLIENT_ID`
   - `AZURE_CLIENT_SECRET`
   - `AZURE_TRUSTED_SIGNING_ACCOUNT`
   - `AZURE_TRUSTED_SIGNING_PROFILE`

### Per-build flow

Use the official `Azure/trusted-signing-action@v0.5.0` GitHub Action.

```yaml
- name: Sign Windows binary
  uses: azure/trusted-signing-action@v0.5.0
  with:
    azure-tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    azure-client-id: ${{ secrets.AZURE_CLIENT_ID }}
    azure-client-secret: ${{ secrets.AZURE_CLIENT_SECRET }}
    endpoint: https://eus.codesigning.azure.net/
    trusted-signing-account-name: ${{ secrets.AZURE_TRUSTED_SIGNING_ACCOUNT }}
    certificate-profile-name: ${{ secrets.AZURE_TRUSTED_SIGNING_PROFILE }}
    files-folder: dist
    files-folder-filter: exe
    file-digest: SHA256
    timestamp-rfc3161: http://timestamp.acs.microsoft.com
    timestamp-digest: SHA256
```

## Linux

PyInstaller `--onefile` produces a static-ish executable. No code
signing infrastructure needed; users either trust the binary or build
from source. Optional later: Flatpak / AppImage / .deb.

## Complete `release-binary.yml` workflow (sketch)

```yaml
name: Build & sign release binaries

on:
  workflow_dispatch:
  push:
    tags: [ 'v*' ]

jobs:
  build-macos:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -e .[dev] pyinstaller
      - name: Import signing cert
        env:
          CERT_B64: ${{ secrets.APPLE_DEVELOPER_ID_CERT }}
          CERT_PW: ${{ secrets.APPLE_DEVELOPER_ID_CERT_PASSWORD }}
        run: |
          echo "$CERT_B64" | base64 -d > cert.p12
          security create-keychain -p actions build.keychain
          security import cert.p12 -k build.keychain -P "$CERT_PW" -T /usr/bin/codesign
          security set-key-partition-list -S apple-tool:,apple: -s -k actions build.keychain
          security default-keychain -s build.keychain
          security unlock-keychain -p actions build.keychain
      - run: pyinstaller packaging/arch-lw.spec --clean --noconfirm
      - name: Notarize
        env:
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_PASSWORD: ${{ secrets.APPLE_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
        run: |
          ditto -c -k --keepParent dist/arch-lw arch-lw-macos.zip
          xcrun notarytool submit arch-lw-macos.zip \
            --apple-id "$APPLE_ID" \
            --password "$APPLE_PASSWORD" \
            --team-id "$APPLE_TEAM_ID" \
            --wait
          xcrun stapler staple dist/arch-lw
      - uses: actions/upload-artifact@v4
        with:
          name: arch-lw-macos
          path: dist/arch-lw

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -e .[dev] pyinstaller
      - run: pyinstaller packaging/arch-lw.spec --clean --noconfirm
      - name: Sign Windows binary
        uses: azure/trusted-signing-action@v0.5.0
        with:
          azure-tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          azure-client-id: ${{ secrets.AZURE_CLIENT_ID }}
          azure-client-secret: ${{ secrets.AZURE_CLIENT_SECRET }}
          endpoint: https://eus.codesigning.azure.net/
          trusted-signing-account-name: ${{ secrets.AZURE_TRUSTED_SIGNING_ACCOUNT }}
          certificate-profile-name: ${{ secrets.AZURE_TRUSTED_SIGNING_PROFILE }}
          files-folder: dist
          files-folder-filter: exe
      - uses: actions/upload-artifact@v4
        with:
          name: arch-lw-windows
          path: dist/arch-lw.exe

  release:
    needs: [build-macos, build-windows]
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/download-artifact@v4
      - run: |
          gh release create "$GITHUB_REF_NAME" \
            --title "$GITHUB_REF_NAME" \
            arch-lw-macos/* arch-lw-windows/*
        env: { GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
```

This file lives at `.github/workflows-disabled/release-binary.yml.disabled`
until Phase D is reached. Move + rename to enable.

## Update / auto-update strategy

For Phase D, **don't ship auto-update.** Reasons:

1. License-key validation is a separate concern; auto-update on a
   pirated copy is a foot-gun.
2. Auto-update requires a stable update server (Sparkle on macOS,
   WinSparkle on Windows, or a custom JSON feed).
3. v1 customers will be small enough to email manually with a
   download link.

For Phase F (web app), auto-update is moot (always on latest).

For Phase G (studio), build a manual `arch-lw self-update` command
that hits a JSON feed and downloads the next signed binary. Verify
the signature before swapping.

## Cost summary — Year 1

| Item | Cost |
|---|---|
| Apple Developer Program | $99 |
| Azure Trusted Signing (~$10/mo × 12) | $120 |
| Domain (`archlineweights.com` or alternative) | ~$12 |
| **Total** | **~$231** |

Optional later:

- Code signing cert for Linux Flatpak: $0 (use Flathub-managed key)
- Sentry self-hosted error reporting: ~$0–26/mo at low volume
- Stripe / Lemon Squeezy fees: per-transaction, not fixed

## Sources

- [PyInstaller documentation](https://pyinstaller.org/en/stable/)
- [Apple — Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Apple — Resolving common notarization issues](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution/resolving_common_notarization_issues)
- [Azure Trusted Signing — overview](https://learn.microsoft.com/en-us/azure/trusted-signing/)
- [Azure Trusted Signing — pricing](https://azure.microsoft.com/en-us/pricing/details/trusted-signing/)
- [Microsoft SmartScreen reputation](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/)
- [GitHub Action: azure/trusted-signing-action](https://github.com/Azure/trusted-signing-action)
- [Heather Meeker — software distribution licensing](https://heathermeeker.com/) (cross-ref to `licensing.md`)

## Related

- `docs/ROADMAP.md` Phase D — distribution v1
- `docs/research/distribution-platforms.md` — where the binaries get sold
- `docs/research/licensing.md` — what the EULA on the binary says
