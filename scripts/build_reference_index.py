#!/usr/bin/env python3
"""Build a private local full-text index for architectural reference books.

The source books and extracted text are intentionally kept out of git. This
script reads ``references/manifest.yml`` and writes a SQLite FTS database under
``data/reference_books/`` so research agents can search page-level excerpts and
return derived notes with page references.
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
    return conn


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    if existing and existing[0] == sha and not force:
        return 0, 0

    doc = fitz.open(book.path)
    page_count = doc.page_count
    page_total = min(page_count, limit_pages) if limit_pages else page_count
    topics = ",".join(book.topics)

    with conn:
        conn.execute("DELETE FROM pages WHERE book_id = ?", (book.id,))
        conn.execute("DELETE FROM page_fts WHERE book_id = ?", (book.id,))
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
        for page_index in range(page_total):
            page_number = page_index + 1
            text = doc.load_page(page_index).get_text("text").strip()
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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--book", action="append", help="Index only one manifest book id. Repeatable.")
    parser.add_argument("--force", action="store_true", help="Re-index even if the source file hash is unchanged.")
    parser.add_argument("--limit-pages", type=int, help="Smoke-test mode: index only the first N pages.")
    parser.add_argument("--query", help="Search an existing or newly built index.")
    parser.add_argument("--query-book", action="append", help="Restrict --query to one manifest book id. Repeatable.")
    parser.add_argument("--query-limit", type=int, default=8)
    return parser.parse_args(argv)


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
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
