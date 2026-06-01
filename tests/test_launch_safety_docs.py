from __future__ import annotations

import re
from pathlib import Path

PUBLIC_SAFETY_SURFACES = [
    Path(".gitattributes"),
    Path("README.md"),
    Path("RELEASE_NOTES.md"),
    Path("SHIP_CHECKLIST.md"),
    Path("docs/CHANGELOG.md"),
    Path("docs/index.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/SESSION_RETRO.md"),
    Path("docs/LESSONS_LEARNED.md"),
    *sorted(Path("docs/announce").glob("*.md")),
    *sorted(Path("docs/how-to").glob("*.md")),
    *sorted(Path("docs/tutorials").glob("*.md")),
]

FORBIDDEN_RETIRED_PROOF_PHRASES = [
    "docs/img/day1-proof",
    "WALL SECTION",
    "wall section iso",
    "section-HIERARCHY-jsx-POCHE.pdf",
    "Proof assets are committed",
    "cut mass solid, openings left white",
    "full section poché",
    "all cut mass black",
    "DRAWING 4 SECTION",
    "USC ARCH 202B drawing",
    "submit-quality path",
    "/Users/",
]

FORBIDDEN_PRIVATE_PROOF_PATTERNS = [
    re.compile(r"iso axon section\s+\[Converted\]", re.IGNORECASE),
    re.compile(r"\bv06\d+[-\w]*\.(?:ai|json)\b", re.IGNORECASE),
    re.compile(r"\biso-axon-v06\d+[-\w]*\.json\b", re.IGNORECASE),
    re.compile(r"<private-arch-202b-root>", re.IGNORECASE),
]


def test_public_docs_do_not_reference_retired_day1_proof_assets() -> None:
    combined = _combined_public_surface_text()

    for phrase in FORBIDDEN_RETIRED_PROOF_PHRASES:
        assert phrase not in combined

    for pattern in FORBIDDEN_PRIVATE_PROOF_PATTERNS:
        assert not pattern.search(combined)


def test_public_docs_keep_posting_gate_visible() -> None:
    combined = _combined_public_surface_text()

    assert "Posting/public proof is NO-GO" in combined
    assert "Synthetic proof does not close #30" in combined


def _combined_public_surface_text() -> str:
    return "\n\n".join(
        path.read_text(encoding="utf-8") for path in PUBLIC_SAFETY_SURFACES if path.exists()
    )
