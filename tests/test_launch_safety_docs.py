from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CORE_PUBLIC_SAFETY_SURFACES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "RELEASE_NOTES.md",
    REPO_ROOT / "SHIP_CHECKLIST.md",
    REPO_ROOT / "mkdocs.yml",
    REPO_ROOT / "webapp" / "README.md",
    REPO_ROOT / "webapp" / "frontend" / "src" / "routes" / "+page.svelte",
    REPO_ROOT / "docs" / "research" / "open-issue-verification-core-handoff-2026-06-01.md",
    *sorted((REPO_ROOT / "docs" / "how-to").rglob("*.md")),
    *sorted((REPO_ROOT / "docs" / "reference").rglob("*.md")),
    *sorted((REPO_ROOT / "docs" / "explanation").rglob("*.md")),
]

# Announce/launch-kit drafts still carry retired Day-1 asset paths until PR #45 lands.
ANNOUNCE_PUBLIC_SAFETY_SURFACES = sorted((REPO_ROOT / "docs" / "announce").rglob("*.md"))

FORBIDDEN_RETIRED_PROOF_PHRASES = [
    "docs/img/day1-proof",
    "WALL SECTION [Converted]",
    "section-HIERARCHY-jsx-POCHE.pdf",
    "Proof assets are committed",
    "cut mass solid, openings left white",
    "full section poché",
    "all cut mass black",
    "DRAWING 4 SECTION",
    "USC ARCH 202B",
    "/Users/",
    "/private/",
    "/var/folders",
    "SynologyDrive",
    "macro_for_archlw",
    "posting is ready",
    "posting ready",
    "App Store is ready",
    "Windows is supported",
    "Windows desktop is supported",
]

FORBIDDEN_PRIVATE_PROOF_PATTERNS = [
    re.compile(r"iso axon section\s+\[Converted\]", re.IGNORECASE),
    re.compile(r"\bv06\d+", re.IGNORECASE),
    re.compile(r"\biso-axon-v06\d+[-\w]*\.json\b", re.IGNORECASE),
    re.compile(r"<private-arch-202b-root>", re.IGNORECASE),
    re.compile(r"[A-Z]:\\"),
]


def test_core_public_surfaces_do_not_reference_retired_day1_proof_assets() -> None:
    combined = _combined_public_surface_text(CORE_PUBLIC_SAFETY_SURFACES)

    for phrase in FORBIDDEN_RETIRED_PROOF_PHRASES:
        assert phrase not in combined, f"forbidden phrase in public surface: {phrase!r}"

    for pattern in FORBIDDEN_PRIVATE_PROOF_PATTERNS:
        assert not pattern.search(combined), f"forbidden pattern matched: {pattern.pattern}"


def test_core_public_surfaces_keep_posting_gate_visible() -> None:
    combined = _combined_public_surface_text(CORE_PUBLIC_SAFETY_SURFACES)

    assert "Posting/public proof is NO-GO" in combined or "NO-GO" in combined
    assert "Synthetic proof does not close #30" in combined
    assert "Private USC regression stays private" in combined


def test_announce_surfaces_still_need_pr45_quarantine() -> None:
    """Track announce/launch-kit debt; remove this test when PR #45 merges."""
    combined = _combined_public_surface_text(ANNOUNCE_PUBLIC_SAFETY_SURFACES)
    assert "docs/img/day1-proof" in combined


def _combined_public_surface_text(paths: list[Path]) -> str:
    return "\n\n".join(path.read_text(encoding="utf-8") for path in paths if path.is_file())
