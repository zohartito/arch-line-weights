"""Fail-closed tombstones for unsupported local processing surfaces."""

from __future__ import annotations

import os


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
