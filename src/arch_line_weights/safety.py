"""Fail-closed tombstones for unsupported local processing surfaces."""

from __future__ import annotations


class ProcessingDisabledError(RuntimeError):
    """Raised before an unsafe processor reads input or allocates work buffers."""


def processing_disabled(surface: str) -> None:
    raise ProcessingDisabledError(
        f"{surface} is permanently disabled: untrusted-input processing has no safe runtime budget"
    )
