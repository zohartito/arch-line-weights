# Reference-Agent Workflow

Date: 2026-05-05

This is the operating model for turning Zohar's private architecture books into
better line-weight and poché behavior.

## Goal

Use the books as a local research library, then convert that research into
tracked, executable project knowledge:

```text
local books -> local page index -> page-cited derived notes -> rulebooks -> tests -> code -> visual QA
```

The agents should read broadly, but the repo should only receive our own
derived rules and citations. Source PDFs, page images, and extracted full text
stay local and gitignored.

## Local Index

Build or refresh the private SQLite index:

```bash
pyenv exec python scripts/build_reference_index.py --force
```

Smoke-test a single book:

```bash
pyenv exec python scripts/build_reference_index.py \
  --book ching_architectural_graphics \
  --limit-pages 20 \
  --force \
  --query 'line weight OR section OR poche'
```

The database lives at:

```text
data/reference_books/reference_pages.sqlite
```

That directory is intentionally ignored by git.

## Agent Wave

Run this as a set of bounded research passes, not as one huge undirected read.
Each agent reads the full assigned source locally, searches the page index for
the target topics, and writes only derived notes.

| Agent | Inputs | Output |
|---|---|---|
| Graphics standards | `Architectural Graphics`, `Design Drawing`, `standards.md` | `docs/research/architectural-graphics-rulebook.md` |
| Poché/materials | `Building Construction Illustrated`, `A Visual Dictionary of Architecture`, `poche-conventions.md` | `docs/research/poche-rulebook.md` |
| Structure hierarchy | `Building Structures Illustrated`, real ARCH 202B layer names | `docs/research/lineweight-rulebook.md` |
| Spatial/readability | `Architecture: Form, Space, and Order`, screenshot QA notes | roadmap additions for hierarchy and depth |
| Codes/annotation | `Building Codes Illustrated`, CLI/reporting docs | annotation/reporting rules, not geometry rules |
| Synthesis | all rule notes + current issues | updated roadmap and issue priorities |

## Extraction Rules

Agents should capture:

- page-cited principles in their own words
- line-weight tier rules
- poché eligibility rules
- "do not poché" counterexamples
- drawing-type differences: plan, section, elevation, axon, detail
- material/assembly semantics that help classify Rhino layers
- unresolved questions that need visual testing

Agents should not capture:

- long quotes
- diagrams copied from the books
- full-page summaries that recreate the books
- source PDFs, rendered book pages, or extracted full text

## Engineering Handoff

Every rulebook section should end with implementation hooks:

- layer-name patterns
- default stroke widths
- poché whitelist/blacklist effects
- geometry confidence requirements
- tests to add
- examples from the iso axon drawing

The synthesis agent then updates:

- `docs/research/professional-grade-roadmap-2026-05-05.md`
- GitHub issues #16, #17, #18, #19, and #20
- `docs/LESSONS_LEARNED.md` when a new failure mode is discovered

## Immediate Product Loop

For Zohar's current deadline drawings, the loop should stay short:

1. Run `arch-lw apply-saas --auto --preset section --poche --bridge-strategy=best`
   with the current hardened defaults.
2. Review the Illustrator output visually.
3. If poché is missing from structural cut material, use the open-loop closure
   work from issue #17.
4. If hierarchy is wrong, use semantic layer rules from issue #16.
5. Log the drawing result and the specific misses.

The research is valuable only when it improves this loop.
