"""Offline tests for the reference-book section tree (scripts/build_reference_index.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import fitz
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_reference_index as bri  # noqa: E402


def _write_book(path: Path, *, outline: bool) -> None:
    doc = fitz.open()
    for number in range(1, 9):
        doc.new_page().insert_text((72, 72), f"Page {number} body text")
    if outline:
        doc.set_toc(
            [
                [1, "Drawing Conventions", 1],
                [2, "Line Weights", 2],
                [2, "Poche", 4],
                [1, "Sections", 6],
            ]
        )
    doc.save(path)
    doc.close()


def _index(tmp_path: Path, *, outline: bool = True, limit_pages: int | None = None):
    pdf = tmp_path / "book.pdf"
    _write_book(pdf, outline=outline)
    manifest = tmp_path / "manifest.yml"
    manifest.write_text(
        f"books:\n  - id: demo\n    title: Demo Book\n    author: A\n    path: {pdf.as_posix()}\n"
    )
    conn = bri.init_db(tmp_path / "index.sqlite")
    (book,) = bri.load_books(manifest)
    bri.index_book(conn, book, force=False, limit_pages=limit_pages)
    return conn, book


def test_index_book_writes_nested_section_tree(tmp_path: Path) -> None:
    conn, _ = _index(tmp_path)
    tree = bri.get_tree(conn, "demo")

    assert [(n["node_id"], n["title"], n["pages"]) for n in tree] == [
        ("0001", "Drawing Conventions", "1-5"),
        ("0004", "Sections", "6-8"),
    ]
    assert [(n["title"], n["pages"]) for n in tree[0]["nodes"]] == [
        ("Line Weights", "2-3"),
        ("Poche", "4-5"),
    ]
    assert tree[0]["nodes"][1]["lead"] == "Page 4 body text"


def test_limit_pages_clamps_tree_and_book_without_outline_gets_root(tmp_path: Path) -> None:
    conn, _ = _index(tmp_path, limit_pages=5)
    assert [(n["title"], n["pages"]) for n in bri.get_tree(conn, "demo")] == [("Drawing Conventions", "1-5")]

    bare_dir = tmp_path / "bare"
    bare_dir.mkdir()
    bare, _ = _index(bare_dir, outline=False)
    assert [(n["title"], n["pages"]) for n in bri.get_tree(bare, "demo")] == [("Demo Book", "1-8")]


def test_unchanged_book_without_tree_is_reindexed(tmp_path: Path) -> None:
    conn, book = _index(tmp_path)
    conn.execute("DELETE FROM sections")
    assert bri.index_book(conn, book, force=False, limit_pages=None) == (8, 8)
    assert bri.get_tree(conn, "demo")
    assert bri.index_book(conn, book, force=False, limit_pages=None) == (0, 0)


def test_get_page_content_expands_validated_spec(tmp_path: Path) -> None:
    conn, _ = _index(tmp_path)
    content = bri.get_page_content(conn, "demo", "1-2, 7")
    assert [(number, text) for number, text in content] == [
        (1, "Page 1 body text"),
        (2, "Page 2 body text"),
        (7, "Page 7 body text"),
    ]


@pytest.mark.parametrize("spec", ["", "0", "3-1", "9", "1-x", "1;2", "-2", "1-2-3"])
def test_parse_page_spec_rejects_bad_specs(spec: str) -> None:
    with pytest.raises(ValueError):
        bri.parse_page_spec(spec, page_count=8)


def test_parse_page_spec_caps_width() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        bri.parse_page_spec("1-51", page_count=100)
