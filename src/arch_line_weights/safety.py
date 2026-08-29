"""Fail-closed tombstones for unsupported local processing surfaces."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO


class ProcessingDisabledError(RuntimeError):
    """Raised before an unsafe processor reads input or allocates work buffers."""


_FREEZE_ENV = "ARCH_LW_FREEZE_LEGACY_APPLY"


def freeze_legacy_apply_enabled() -> bool:
    """Return True when legacy apply/inspect/poche processors must fail closed.

    Default is off so the documented byte-idempotent ``arch-lw apply`` path
    (and the audit that depends on it) keeps working. Set
    ``ARCH_LW_FREEZE_LEGACY_APPLY=1`` to opt into the kill-switch.
    """
    return os.environ.get(_FREEZE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def processing_disabled(surface: str) -> None:
    """Raise when the legacy-apply freeze env var is set; otherwise no-op."""
    if not freeze_legacy_apply_enabled():
        return
    raise ProcessingDisabledError(
        f"{surface} is permanently disabled: untrusted-input processing has no safe runtime budget "
        f"(set {_FREEZE_ENV}=0 or unset to re-enable)"
    )


def private_temp_dir(*, prefix: str = "arch-lw-") -> Path:
    """Create a mode-0700, per-run directory for transient helper files.

    Generated JSX, progress, and report paths must never share predictable
    names directly under the system temporary directory.  The private parent
    directory prevents another local user from prepositioning a symlink at a
    child path before Illustrator or a helper opens it.
    """
    path = Path(tempfile.mkdtemp(prefix=prefix))
    # mkdtemp creates mode 0700 on supported platforms; enforce it explicitly
    # so a permissive process umask cannot weaken the ownership boundary.
    os.chmod(path, 0o700)
    return path


def cleanup_private_temp_dir(path: Path) -> None:
    """Remove an auto-created private work directory after its run ends."""
    # Callers may defensively clean the same owned directory twice while
    # unwinding an initialization failure.  A missing directory is harmless;
    # any real removal failure must surface rather than leaving private output
    # behind unnoticed.
    if path.exists():
        shutil.rmtree(path)


@contextmanager
def private_temp_directory(*, prefix: str = "arch-lw-") -> Iterator[Path]:
    """Yield a private temporary directory and remove it on every exit path."""
    path = private_temp_dir(prefix=prefix)
    try:
        yield path
    finally:
        cleanup_private_temp_dir(path)


def open_private_temp_file(directory: Path, name: str) -> IO[str]:
    """Exclusively create a mode-0600 file below a private work directory."""
    if Path(name).name != name:
        raise ValueError("private temporary file name must be a basename")
    dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    dir_fd = os.open(directory, dir_flags)
    try:
        file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        file_fd = os.open(name, file_flags, 0o600, dir_fd=dir_fd)
    finally:
        os.close(dir_fd)
    return os.fdopen(file_fd, "w", encoding="utf-8", buffering=1)


def terminal_safe(value: object) -> str:
    """Render data for a terminal without allowing terminal control bytes.

    Keep printable Unicode intact while making C0, DEL, and C1 controls
    visible.  This includes ESC, BEL, carriage return, and embedded newlines.
    """
    rendered = str(value)
    safe: list[str] = []
    for char in rendered:
        code = ord(char)
        if code < 0x20 or 0x7F <= code <= 0x9F:
            safe.append(f"\\x{code:02x}" if code <= 0xFF else f"\\u{code:04x}")
        else:
            safe.append(char)
    return "".join(safe)
