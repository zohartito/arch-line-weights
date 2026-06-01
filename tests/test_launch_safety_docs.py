from __future__ import annotations

from pathlib import Path

PUBLIC_DOCS = [
    Path("README.md"),
    Path("RELEASE_NOTES.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/SESSION_RETRO.md"),
    Path("docs/LESSONS_LEARNED.md"),
    *sorted(Path("docs/announce").glob("*.md")),
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
]


def test_public_docs_do_not_reference_retired_day1_proof_assets() -> None:
    combined = "\n\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_DOCS)

    for phrase in FORBIDDEN_RETIRED_PROOF_PHRASES:
        assert phrase not in combined


def test_public_docs_keep_posting_gate_visible() -> None:
    combined = "\n\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_DOCS)

    assert "Posting/public proof is NO-GO" in combined
    assert "Synthetic proof does not close #30" in combined
