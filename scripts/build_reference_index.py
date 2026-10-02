#!/usr/bin/env python3
"""Build a private local full-text index for architectural reference books.

The source books and extracted text are intentionally kept out of git. This
script reads ``references/manifest.yml`` and writes a SQLite FTS database under
``data/reference_books/`` so research agents can search page-level excerpts and
return derived notes with page references.

Next to the full-text index it stores a per-book section tree (node_id, title,
page range, short lead) built deterministically from the PDF outline, so an
agent can navigate a book with ``--tree`` and then read exact pages with
``--read BOOK --pages '1-3,7'`` instead of scanning FTS hits.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "references" / "manifest.yml"
DEFAULT_DB = REPO_ROOT / "data" / "reference_books" / "reference_pages.sqlite"
LEAD_CHARS = 160
MAX_PAGE_SPEC_PAGES = 50


@dataclass(frozen=True)
class Book:
    id: str
    title: str
    author: str
    path: Path
    priority: int
    topics: tuple[str, ...]


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise SystemExit(
            "PyYAML is required to read references/manifest.yml. "
            "Install it in your local dev env with `pip install PyYAML`."
        ) from exc
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"Manifest did not parse to a mapping: {path}")
    return data


def load_books(manifest_path: Path) -> list[Book]:
    manifest = _load_yaml(manifest_path)
    raw_books = manifest.get("books")
    if not isinstance(raw_books, list):
        raise SystemExit(f"Manifest has no `books` list: {manifest_path}")

    books: list[Book] = []
    for raw in raw_books:
        if not isinstance(raw, dict):
            raise SystemExit(f"Invalid book entry in {manifest_path}: {raw!r}")
        topics = raw.get("topics", [])
        if not isinstance(topics, list):
            raise SystemExit(f"Book topics must be a list: {raw.get('id')}")
        books.append(
            Book(
                id=str(raw["id"]),
                title=str(raw["title"]),
                author=str(raw["author"]),
                path=Path(str(raw["path"])).expanduser(),
                priority=int(raw.get("priority", 99)),
                topics=tuple(str(topic) for topic in topics),
            )
        )
    return books


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            priority INTEGER NOT NULL,
            topics TEXT NOT NULL,
            indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (
            book_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            PRIMARY KEY (book_id, page_number),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS page_fts
        USING fts5(book_id, title, author, topics, page_number UNINDEXED, text)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sections (
            book_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            parent_id TEXT,
            level INTEGER NOT NULL,
            title TEXT NOT NULL,
            start_page INTEGER NOT NULL,
            end_page INTEGER NOT NULL,
            lead TEXT NOT NULL,
            PRIMARY KEY (book_id, node_id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
        """
    )
    return conn


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_section_tree(
    toc: list[list[Any]], page_texts: list[str], fallback_title: str
) -> list[tuple[str, str | None, int, str, int, int, str]]:
    """Flatten a PDF outline into (node_id, parent_id, level, title, start, end, lead) rows.

    A node ends the page before the next node at the same or a shallower level
    starts, so every range nests inside its parent. Outline entries pointing
    past the indexed pages are dropped; a book without an outline becomes one
    root node spanning every indexed page.
    """
    page_total = len(page_texts)
    entries = [
        (int(level), str(title).strip(), int(page))
        for level, title, page, *_ in toc
        if 1 <= int(page) <= page_total and str(title).strip()
    ]
    if not entries and page_total:
        entries = [(1, fallback_title, 1)]

    rows: list[tuple[str, str | None, int, str, int, int, str]] = []
    stack: list[tuple[int, str]] = []
    for index, (level, title, start) in enumerate(entries):
        node_id = f"{index + 1:04d}"
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent_id = stack[-1][1] if stack else None
        stack.append((level, node_id))
        next_start = next((s for lvl, _, s in entries[index + 1 :] if lvl <= level), page_total + 1)
        end = max(start, next_start - 1)
        lead = " ".join(page_texts[start - 1].split())[:LEAD_CHARS]
        rows.append((node_id, parent_id, level, title, start, end, lead))
    return rows


def index_book(
    conn: sqlite3.Connection,
    book: Book,
    *,
    force: bool,
    limit_pages: int | None,
) -> tuple[int, int]:
    if not book.path.exists():
        raise FileNotFoundError(book.path)

    sha = file_sha256(book.path)
    existing = conn.execute("SELECT sha256 FROM books WHERE id = ?", (book.id,)).fetchone()
    has_tree = conn.execute("SELECT 1 FROM sections WHERE book_id = ? LIMIT 1", (book.id,)).fetchone()
    if existing and existing[0] == sha and has_tree and not force:
        return 0, 0

    doc = fitz.open(book.path)
    page_count = doc.page_count
    page_total = min(page_count, limit_pages) if limit_pages else page_count
    topics = ",".join(book.topics)

    with conn:
        conn.execute("DELETE FROM pages WHERE book_id = ?", (book.id,))
        conn.execute("DELETE FROM page_fts WHERE book_id = ?", (book.id,))
        conn.execute("DELETE FROM sections WHERE book_id = ?", (book.id,))
        conn.execute(
            """
            INSERT OR REPLACE INTO books
                (id, title, author, path, sha256, page_count, priority, topics, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                book.id,
                book.title,
                book.author,
                str(book.path),
                sha,
                page_count,
                book.priority,
                topics,
            ),
        )
        page_texts: list[str] = []
        for page_index in range(page_total):
            page_number = page_index + 1
            text = doc.load_page(page_index).get_text("text").strip()
            page_texts.append(text)
            conn.execute(
                """
                INSERT INTO pages (book_id, page_number, text, char_count)
                VALUES (?, ?, ?, ?)
                """,
                (book.id, page_number, text, len(text)),
            )
            conn.execute(
                """
                INSERT INTO page_fts (book_id, title, author, topics, page_number, text)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (book.id, book.title, book.author, topics, page_number, text),
            )
        conn.executemany(
            """
            INSERT INTO sections
                (book_id, node_id, parent_id, level, title, start_page, end_page, lead)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(book.id, *row) for row in build_section_tree(doc.get_toc(simple=True), page_texts, book.title)],
        )
    doc.close()
    return page_total, page_count


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int,
    book_ids: set[str] | None,
) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    if book_ids:
        placeholders = ", ".join("?" for _ in book_ids)
        return conn.execute(
            f"""
            SELECT
                book_id,
                title,
                page_number,
                snippet(page_fts, 5, '[', ']', ' ... ', 28) AS snippet
            FROM page_fts
            WHERE page_fts MATCH ?
                AND book_id IN ({placeholders})
            ORDER BY bm25(page_fts)
            LIMIT ?
            """,
            (query, *sorted(book_ids), limit),
        ).fetchall()
    return conn.execute(
        """
        SELECT
            book_id,
            title,
            page_number,
            snippet(page_fts, 5, '[', ']', ' ... ', 28) AS snippet
        FROM page_fts
        WHERE page_fts MATCH ?
        ORDER BY bm25(page_fts)
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()


def get_tree(conn: sqlite3.Connection, book_id: str) -> list[dict[str, Any]]:
    """Return a book's section tree as nested dicts (children under ``nodes``)."""
    nodes: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []
    for node_id, parent_id, title, start, end, lead in conn.execute(
        """
        SELECT node_id, parent_id, title, start_page, end_page, lead
        FROM sections WHERE book_id = ? ORDER BY node_id
        """,
        (book_id,),
    ):
        node = {"node_id": node_id, "title": title, "pages": f"{start}-{end}", "lead": lead, "nodes": []}
        nodes[node_id] = node
        (nodes[parent_id]["nodes"] if parent_id in nodes else roots).append(node)
    return roots


def parse_page_spec(spec: str, page_count: int) -> list[int]:
    """Expand a page spec like ``'1-3,7'`` into sorted unique page numbers.

    Raises ``ValueError`` on malformed tokens, reversed or out-of-range pages,
    or a request wider than ``MAX_PAGE_SPEC_PAGES``.
    """
    pages: set[int] = set()
    for token in spec.split(","):
        start_text, _, end_text = token.strip().partition("-")
        end_text = end_text or start_text
        if not (start_text.isdigit() and end_text.isdigit()):
            raise ValueError(f"invalid page token {token.strip()!r} in {spec!r}")
        start, end = int(start_text), int(end_text)
        if not 1 <= start <= end <= page_count:
            raise ValueError(f"page range {start}-{end} outside 1-{page_count}")
        pages.update(range(start, end + 1))
        if len(pages) > MAX_PAGE_SPEC_PAGES:
            raise ValueError(f"page spec {spec!r} exceeds {MAX_PAGE_SPEC_PAGES} pages")
    return sorted(pages)


def get_page_content(conn: sqlite3.Connection, book_id: str, spec: str) -> list[tuple[int, str]]:
    """Return ``(page_number, text)`` for the indexed pages named by ``spec``."""
    (page_count,) = conn.execute(
        "SELECT COALESCE(MAX(page_number), 0) FROM pages WHERE book_id = ?", (book_id,)
    ).fetchone()
    if not page_count:
        raise ValueError(f"book {book_id!r} is not indexed")
    pages = parse_page_spec(spec, page_count)
    placeholders = ", ".join("?" for _ in pages)
    return conn.execute(
        f"""
        SELECT page_number, text FROM pages
        WHERE book_id = ? AND page_number IN ({placeholders})
        ORDER BY page_number
        """,
        (book_id, *pages),
    ).fetchall()


def _print_tree(nodes: list[dict[str, Any]], depth: int = 0) -> None:
    for node in nodes:
        print(f"{'  ' * depth}[{node['node_id']}] {node['title']} (pp. {node['pages']})")
        _print_tree(node["nodes"], depth + 1)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--book", action="append", help="Index only one manifest book id. Repeatable.")
    parser.add_argument(
        "--force", action="store_true", help="Re-index even if the source file hash is unchanged."
    )
    parser.add_argument("--limit-pages", type=int, help="Smoke-test mode: index only the first N pages.")
    parser.add_argument("--query", help="Search an existing or newly built index.")
    parser.add_argument(
        "--query-book", action="append", help="Restrict --query to one manifest book id. Repeatable."
    )
    parser.add_argument("--query-limit", type=int, default=8)
    parser.add_argument("--tree", metavar="BOOK_ID", help="Print one book's section tree.")
    parser.add_argument("--read", metavar="BOOK_ID", help="Print page text for --pages from one book.")
    parser.add_argument("--pages", help="Page spec for --read, e.g. '1-3,7'.")
    args = parser.parse_args(argv)
    if bool(args.read) != bool(args.pages):
        parser.error("--read and --pages must be used together")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    books = load_books(args.manifest)
    if args.book:
        wanted = set(args.book)
        books = [book for book in books if book.id in wanted]
        missing = wanted - {book.id for book in books}
        if missing:
            raise SystemExit(f"Unknown book id(s): {', '.join(sorted(missing))}")

    conn = init_db(args.db)
    total_pages = 0
    skipped = 0
    for book in sorted(books, key=lambda item: (item.priority, item.id)):
        indexed_pages, page_count = index_book(
            conn,
            book,
            force=args.force,
            limit_pages=args.limit_pages,
        )
        if indexed_pages == 0:
            skipped += 1
            print(f"skip unchanged: {book.id}")
        else:
            total_pages += indexed_pages
            suffix = f"/{page_count}" if indexed_pages != page_count else ""
            print(f"indexed {book.id}: {indexed_pages}{suffix} pages")

    print(f"database: {args.db}")
    print(f"books processed: {len(books) - skipped} indexed, {skipped} unchanged")
    print(f"pages indexed this run: {total_pages}")

    if args.query:
        print()
        query_books = set(args.query_book or [])
        for row in search(conn, args.query, limit=args.query_limit, book_ids=query_books or None):
            print(f"{row['title']} p.{row['page_number']} ({row['book_id']})")
            print(f"  {row['snippet']}")
    if args.tree:
        print()
        _print_tree(get_tree(conn, args.tree))
    if args.read:
        print()
        try:
            content = get_page_content(conn, args.read, args.pages)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        for page_number, text in content:
            print(f"--- {args.read} p.{page_number} ---")
            print(text)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
