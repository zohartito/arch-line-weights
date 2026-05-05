# Architectural Reference Library

Date: 2026-05-05

## Decision

Do not commit source books or downloaded PDFs to GitHub.

Many of the local files are copyrighted books. The project can use them as a
private reference library on the user's machine, but the repo should only store:

- a manifest of local paths
- extracted metadata
- page-level private indexes ignored by git
- short derived notes and implementation rules
- citations/page references

The useful product artifact is not a copy of the books. It is a professional
architectural-graphics standard distilled into rules that the code can execute.

## Local Source Folder

```text
/Users/zohartito/SynologyDrive/7-17-2024 Backup/untitled folder/school/school books
```

Initial priority books:

```text
Architectural Graphics (Francis D. K. Ching) (z-lib.org).pdf
A Visual Dictionary of Architecture (Francis D. K. Ching) (z-lib.org).pdf
Architecture Form, Space, and Order (Francis D. K. Ching) (z-lib.org).pdf
Building Construction Illustrated (Francis D. K. Ching) (z-lib.org).pdf
Building Structures Illustrated Patterns, Systems, and Design (Francis D. K. Ching) (z-lib.org).pdf
Design Drawing (Francis D.K. Ching, Steven P. Juroszek) (z-lib.org).pdf
Building Codes Illustrated A Guide to Understanding the 2018 International Building Code (Francis D. K. Ching, Steven R. Winkel) (z-lib.org).pdf
```

## Proposed Local Index

Ignored by git:

```text
data/reference_books/
  reference_pages.sqlite
  page_images/
  extracted_text/
```

Tracked by git:

```text
references/
  manifest.yml
docs/research/architectural-graphics-rulebook.md
docs/research/lineweight-rulebook.md
docs/research/poche-rulebook.md
docs/research/entourage-rulebook.md
```

## Ingestion Workflow

1. Create a manifest with title, author, local path, and topic tags.
2. Extract page text with `scripts/build_reference_index.py`.
3. Render selected pages to images for visual review because architectural
   graphics knowledge is diagram-heavy.
4. Store extracted text and thumbnails in ignored local storage.
5. Build SQLite FTS search first; add embeddings later only if needed.
6. Write short derived rules with page references.
7. Convert rules into classifier tests and implementation.

Smoke test:

```bash
pyenv exec python scripts/build_reference_index.py \
  --book ching_architectural_graphics \
  --limit-pages 20 \
  --force \
  --query 'line weight OR section OR poche'
```

Full local build:

```bash
pyenv exec python scripts/build_reference_index.py --force
```

See `docs/research/reference-agent-workflow.md` for the agent handoff.

## Copyright Boundary

Allowed:

- summarize concepts
- cite book title/page numbers
- extract short quotes only when needed and within fair-use limits
- create implementation rules in our own words
- keep private indexes local and gitignored

Not allowed:

- commit the PDFs or EPUBs
- publish large extracted text
- reproduce diagrams or long passages
- use z-lib filenames as distributable assets

## Product Impact

The reference library should directly inform:

- hierarchy classifier rules
- poché eligibility rules
- material hatch library
- entourage placement/style rules
- print vs screen presets
- visual QA rubrics
