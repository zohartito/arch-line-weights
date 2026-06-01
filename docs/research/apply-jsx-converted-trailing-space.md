# apply-jsx [Converted] matcher — trailing-space edge case (Issue #14)

> Implementation notes for the v0.6.1+ extension of the
> `_is_converted_match` helper in `apply_jsx.py`. Companion to
> `apply-jsx-bugfixes-notes.md`, which documents the original v0.5.2
> Issue #10 fix.

## Symptom

The user has a Rhino-exported drawing on disk literally named

```
<local-drawing-folder>/sample section cut .ai
```

— note the **trailing space** before `.ai`. (Most filesystems allow
this; Rhino's exporter produces it when the layer name itself ended in
a space. macOS APFS preserves it byte-for-byte.)

When this file is double-clicked into Illustrator, AI strips the
extension, sees a stem ending in a single space, and renders the doc
title as

```
sample section cut  [Converted].ai
```

— with **two spaces** between `cut` and `[Converted]` (one from the
disk stem's trailing space, one inserted by Illustrator before
`[Converted]`).

The pre-Issue-#14 matcher built four candidate suffixes from the source
basename:

```
"<basename> [Converted]"
"<basename> [Converted].ai"
"<stem> [Converted]"
"<stem> [Converted].ai"
```

For our trailing-space disk file:

| candidate                                         | active doc name (Illustrator)        | match?
|---------------------------------------------------|-------------------------------------|------
| `sample section cut .ai [Converted]`            | `sample section cut  [Converted].ai` | no — `.ai` in the wrong position
| `sample section cut .ai [Converted].ai`         | …                                    | no — same problem
| `sample section cut  [Converted]`               | …                                    | no — Illustrator's name has `.ai`
| `sample section cut  [Converted].ai`            | `sample section cut  [Converted].ai` | **would match exactly**

So in principle the fourth candidate should have matched. In practice
the active-doc-name shape Illustrator returns sometimes strips the
trailing whitespace from the stem (Illustrator's display logic is
inconsistent across versions), giving e.g.

```
sample section cut [Converted].ai
```

— **one space** between `cut` and `[Converted]`. None of the candidate
suffixes match that shape because the source-side `<stem>` still has
its literal trailing space.

The fall-through then went to the `open POSIX file` step. AppleScript
silently no-op's on `[Converted]` virtual docs, the JSX couldn't find
its target, and the user saw `ERROR: target doc not open`.

## Fix — normalize trailing whitespace on both sides

`_is_converted_match` now:

1. **Peels the `[Converted]` decoration** from the active-doc name via
   a regex (`\s*\[Converted\]\s*(?:\.[A-Za-z0-9]+)?\s*$`) that handles
   leading/trailing whitespace around the token AND the optional
   re-appended extension.
2. **Strips trailing whitespace** from both the source stem and the
   active-doc stem (`str.rstrip()`, full Unicode whitespace — covers
   spaces, tabs, NBSP, etc.).
3. **Compares normalized stems** for equality. If they match AND the
   `[Converted]` token is in the active-doc name, it's a match.
4. Falls back to the legacy candidate-suffix sweep (now includes the
   normalized stem variants) for any pre-existing exact-name shape we
   already supported.
5. The path-consistency check is unchanged: if AppleScript reported a
   saved path for the active doc, it must point at the same file as
   `src`.

The matcher is ALSO restricted to require the literal `[Converted]`
substring before doing the primary stem comparison — otherwise a
saved doc whose path equals `src` (no `[Converted]` decoration) would
falsely match through the new code path. The wrapper relies on a
`False` return there to fall through to the standard `open POSIX file`
flow.

## query_active_doc — preserve internal whitespace

`query_active_doc()` previously called `.strip()` on the entire
`osascript` stdout, which would have damaged a doc name ending in
whitespace if osascript ever returned the name as the last token. We
switched to `rstrip("\r\n")` so we only trim the newline osascript
appends, preserving any trailing whitespace inside the name field.

In practice the doc name is followed by `|<path>` so the trailing
chars are never internal whitespace anyway, but the conservative
trim removes a class of future regressions.

## Test coverage

`tests/test_apply_jsx_converted_match.py` exercises the contract
across a matrix of adversarial whitespace forms:

| case                                    | match
|-----------------------------------------|------
| trailing space in disk filename         | yes
| no extension in active-doc name         | yes
| leading space in active-doc name        | yes
| multiple internal spaces (preserved)    | yes
| tab character before extension          | yes
| Unicode NBSP (U+00A0) before extension  | yes
| mixed run of space + tab + NBSP         | yes
| unrelated basename                      | no
| saved doc with no `[Converted]`         | no (even when path == src)
| `[Converted]` with mismatched saved path | no
| empty stem (`[Converted].ai`)           | no

Plus parametrized helper-level coverage for `_normalize_stem` and
`_strip_converted_decoration`.

## Cross-cutting note

This is the same class of bug as Issue #10 in spirit — Illustrator's
display name doesn't quite match the filesystem and the matcher has
to bridge the gap. The lesson logged in POSTMORTEM Attempt 9 still
holds: **whenever the matcher must compare a filesystem name against
an Illustrator display name, normalize whitespace and decoration on
both sides before comparing**.
