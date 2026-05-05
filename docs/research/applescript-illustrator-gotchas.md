# AppleScript ↔ Illustrator gotchas — permanent reference

> Failure-mode catalogue for the `osascript` / `do javascript` /
> `current document` bridge that `apply-jsx` rides on. Every entry
> below cost real time and shipped a regression at least once. Keep
> them here so the next person debugging the JSX path can search
> instead of rediscovering.
>
> Companion to: `apply-jsx-bugfixes-notes.md` (Issues #8/#10/#11/#13),
> `apply-jsx-converted-trailing-space.md` (Issue #14), and
> `docs/POSTMORTEM.md` Attempt 9.
>
> Source under test: `src/arch_line_weights/apply_jsx.py`.

## 1. `name of active document` parser failure on Illustrator 2026

**Symptom.** `osascript` exits 1 with
`Expected end of line, but found class name. (-2741)`.

**Trigger.** The literal AppleScript

```applescript
tell application "Adobe Illustrator"
  set docName to name of active document
end tell
```

works on Illustrator 2024 / 2025, but fails on Illustrator 2026
(Adobe build 30.x). The dictionary on 2026 has both a `name` *property*
and a `name` *class*, and the parser cannot disambiguate the noun
phrase at this exact token sequence.

**Fix.** Two adjustments combined reliably; either alone is fragile:

1. Use **`current document`** instead of `active document`. Same
   semantics, distinct dictionary path.
2. Wrap the property access in **`(get name of current document)`** so
   the parser binds the property to the receiver explicitly.

Working form (the one shipped in `apply_jsx.py::query_active_doc`):

```applescript
tell application "Adobe Illustrator"
  if (count of documents) is 0 then
    return ""
  end if
  set docName to (get name of current document)
  try
    set docPath to POSIX path of (file path of current document)
  on error
    set docPath to ""
  end try
  return docName & "|" & docPath
end tell
```

**Cited.** v0.6.4 (`5641ddf`). Originally introduced in v0.6.1 as part
of Issue #10; shipped broken on 2026 because all unit tests mocked
`subprocess.run`, so neither `osascript` nor `osacompile` ever saw the
literal. Issue #10 + the v0.6.5 integration tests are the regression
backstop.

## 2. `[Converted]` virtual document state

**Symptom.** `apply-jsx` prints `ERROR: target doc not open: <path>`
even though Illustrator clearly has the file open. AppleScript
`open POSIX file "..."` returns silently a few seconds before; the JSX
then can't find the target by `fullName.fsName`.

**Trigger.** When Illustrator opens any non-AI source — a PDF, an older
`.ai`, or anything Illustrator considers foreign — it loads the file
into a *virtual* document titled `<basename> [Converted]`. The disk file
is unmodified and there is no in-memory `Document` whose `fullName.fsName`
matches the disk path. `tell application "Adobe Illustrator" to open
POSIX file "..."` is a no-op against a `[Converted]` doc.

**Fix.** Two-pronged in `apply_jsx.py`:

1. Pre-flight call to `query_active_doc()` to read the active doc name
   + saved path.
2. If the active doc name contains `[Converted]` and `_is_converted_match`
   recognizes it as the same file as `src` (after whitespace
   normalization, see #4), set `USE_OPEN_DOC=true` in the rendered JSX.
   The JSX then runs against `app.activeDocument` directly and skips
   the brittle `open POSIX file` step.

**Cited.** Issue #10, v0.6.1 (`d97c2be`). Required v0.6.4 to actually
fire because of #1 above.

## 3. Disk filenames with trailing whitespace

**Symptom.** A Rhino-exported file literally named
`wall section iso cut .ai` (note the trailing space before `.ai`) was
opened in Illustrator as `wall section iso cut  [Converted].ai` (two
spaces between `cut` and `[Converted]`), and the v0.6.1 `_is_converted_match`
helper failed to recognize the relationship.

**Trigger.** APFS preserves trailing whitespace in filenames byte-for-byte.
Rhino's exporter produces such names whenever the source layer name ends
in a space — which is common because Rhino doesn't strip trailing
whitespace from layer names. Illustrator's display logic is *also*
inconsistent across versions: sometimes it preserves the trailing space
(yielding two consecutive spaces before `[Converted]`), sometimes it
strips it (yielding one).

**Fix.** `_is_converted_match` now:

1. Peels the `[Converted]` decoration via the regex
   `\s*\[Converted\]\s*(?:\.[A-Za-z0-9]+)?\s*$`.
2. Strips trailing whitespace via `str.rstrip()` (full Unicode — covers
   ASCII space, tab, NBSP, U+00A0, etc.) on **both** sides.
3. Compares the normalized stems for equality.
4. Falls back to a legacy candidate-suffix sweep for pre-existing exact
   shapes.

`query_active_doc()` correspondingly switched from `.strip()` to
`rstrip("\r\n")` so trailing whitespace inside the doc-name field
survives the osascript round-trip.

**Cited.** Issue #14, v0.6.3 (`087f402`). 24 test cases in
`tests/test_apply_jsx_converted_match.py` cover the full whitespace
matrix. See also `docs/research/apply-jsx-converted-trailing-space.md`.

## 4. `osacompile` vs `osascript -e` — quoting and `\n` handling

**Symptom.** A test that piped a heredoc through `osascript -e` passed,
but the same literal compiled via `osacompile` failed. Or vice versa.

**Trigger.** The two tools take input differently:

- `osascript -e '<script>'` accepts a single string; `\n` inside that
  string is **literal** unless your shell interpolates it. AppleScript
  itself uses `\r` (CR) for line breaks at the source level when written
  via `-e`. Multi-line scripts via `-e` typically use one `-e` per line.
- `osacompile -o out.scpt in.applescript` reads a file. Source uses
  newlines (LF or CR) directly; `\n` in the file is **literal `\n`** and
  will fail to compile.

In `apply_jsx.py::query_active_doc`, the AppleScript literal uses
explicit `\n` characters in a Python triple-string. When passed to
`subprocess.run(["osascript", "-e", script], ...)`, Python sends the
string with real newline bytes — `osascript -e` accepts that on macOS
13+. The integration test
`test_applescript_syntax_compiles` (v0.6.5) writes the *same* literal
to a temp `.applescript` file and runs `osacompile` against it; that
verifies the source survives both ingestion paths. Both must pass for
the bridge to be safe in production.

**Recipe.** When in doubt, prefer real newlines in the Python literal
over `\n` escapes. Treat any AppleScript that round-trips through
`osascript -e` as suspect until `osacompile` has accepted the same
bytes.

**Cited.** v0.6.5 (`6c965bd`), `tests/integration/test_apply_jsx_applescript.py`.
v0.6.6 (`e7f6363`) added the `_illustrator_installed()` skip predicate
because `osacompile` cannot resolve Illustrator's dictionary classes
on machines without Illustrator installed (CI runners).

## 5. The 120-second AppleScript default timeout

**Symptom.** Long-running JSX (Illustrator chewing on 100K+ paths)
gets killed at exactly 120 s by AppleScript even though Illustrator
itself is still working. The user sees an `Apple event timed out
(-1712)` error from `osascript`.

**Trigger.** AppleScript's default timeout for any `tell` block is
**120 seconds**. Long `do javascript` payloads exceed this routinely.

**Fix.** Wrap every `tell application "Adobe Illustrator"` block in
`with timeout of N seconds`:

```applescript
with timeout of 1800 seconds
  tell application "Adobe Illustrator"
    do javascript (read POSIX file "/tmp/arch_lw_apply.jsx" as «class utf8»)
  end tell
end timeout
```

`apply_jsx.py::run_jsx_in_illustrator` uses `timeout` parameter (default
3600 s) and `apply_jsx.py::open_in_illustrator` uses 1800 s. The
subprocess-side `subprocess.run(..., timeout=timeout + 60)` is an
outer guard that adds 60 s of grace.

**Cited.** Lesson #13 in `docs/LESSONS_LEARNED.md`; Issue #11 (v0.6.1,
`d97c2be`) made the inner number configurable via `--timeout MINUTES`
and the `ARCH_LW_JSX_TIMEOUT_MIN` env var because 60 min was wrong both
ways (waste on small files, false-abort on big ones).

## 6. The `do javascript` ExtendScript bridge

**Symptom.** The JSX inside `apply_jsx.py::JSX_TEMPLATE` runs fine when
double-clicked into Illustrator's Scripts panel but throws
`SyntaxError` or returns silently when invoked through
`do javascript ... as «class utf8»`.

**Trigger.** Two common mistakes:

1. **Encoding cast missing** — `do javascript (read POSIX file "X")`
   reads as MacRoman by default. The `as «class utf8»` cast is required
   for any non-ASCII content (and any source that may contain emdashes,
   smart quotes, or comments in non-English text).
2. **ExtendScript is ES3-ish.** No `let`, no arrow functions, no
   `Array.prototype.find`, no native `JSON`. The JSX template uses
   `var`, plain `function`, and explicit string concatenation. Polyfills
   exist but the simpler fix is staying in vanilla.

**Fix.** Always read with `as «class utf8»`; always lint the JSX
against ExtendScript-compatible syntax. The `apply_jsx.py` template is
the canonical reference; copy from it rather than re-deriving.

**Cited.** Lessons #17, #18 in `docs/LESSONS_LEARNED.md`. The
`run_jsx_in_illustrator` helper.

## 7. `osascript` patterns to test with — what works and what fails

Quick reference table for the syntaxes we've actually exercised in
production. `IL = Illustrator`.

| Form                                          | Works on Illustrator 2024+ | Works on 2026 (build 30.x) | Notes |
|-----------------------------------------------|---------------------------|----------------------------|-------|
| `name of active document`                     | ✅                         | ❌ (-2741)                  | Fail #1 above. Use `current document`. |
| `name of current document`                    | ✅                         | ❌ (-2741) sometimes        | Wrap in `(get …)`. |
| `(get name of current document)`              | ✅                         | ✅                          | Canonical form. |
| `POSIX path of (file path of current document)` | ✅                       | ✅                          | Wrap in `try` — virtual `[Converted]` docs raise. |
| `POSIX path of (file path of active document)`  | ✅                       | ⚠️ flaky                    | Same `name`-class ambiguity infects siblings. |
| `count of documents`                          | ✅                         | ✅                          | Always check before accessing `current document`. |
| `tell IL to open POSIX file "X"` against saved doc | ✅                    | ✅                          | Standard happy path. |
| `tell IL to open POSIX file "X"` against `[Converted]` doc | ❌            | ❌                          | Silently no-ops. Fail #2. Use `USE_OPEN_DOC` mode. |
| `do javascript "..."` (inline)                | ✅                         | ✅                          | Beware shell quoting nightmares for >1 line. |
| `do javascript (read POSIX file "X")` (no cast) | ⚠️ MacRoman              | ⚠️ MacRoman                 | Add `as «class utf8»`. |
| `do javascript (read POSIX file "X" as «class utf8»)` | ✅                | ✅                          | Canonical form. |
| `with timeout of N seconds … end timeout`     | ✅                         | ✅                          | Default is 120 s — always wrap. |

**Cited.** Aggregate of all of the above; tested live during
v0.6.4 / v0.6.5 against the user's Illustrator 2026 build 30.3.0
on macOS 14 Sonoma.

## 8. Sanity-check matrix for any future change to `query_active_doc`

If you touch the AppleScript literal in `apply_jsx.py`, run all three:

1. **`osacompile` syntax check** — proves the literal parses against
   the installed Illustrator dictionary (`tests/integration/`).
2. **`osascript` live execution** — proves the bound semantics work
   against a running Illustrator.
3. **Real `[Converted]` doc test** — open a non-AI source (any PDF will
   do), then run `apply-jsx` against the disk path. Wrapper should
   print the `# detected [Converted] doc …` line.

Don't trust `subprocess.run` mocks alone. Both v0.6.1 and v0.6.3
shipped with broken AppleScript because the unit tests passed against
mocks while the literal was rejected by the parser. v0.6.5 added the
syntax-compile integration test specifically to plug this regression
class.

**Cited.** v0.6.5 commit message + the postmortem note in v0.6.6 (CI
fix when Illustrator isn't installed at all on the runner).

## See also

- `docs/POSTMORTEM.md` Attempt 9 — narrative of the run that surfaced
  Issues #8/#10/#11/#13.
- `docs/LESSONS_LEARNED.md` lessons #10–#18 and #44 — durable form of
  the lessons distilled here.
- `docs/research/apply-jsx-bugfixes-notes.md` — implementation details
  for the v0.6.1 fix cluster.
- `docs/research/apply-jsx-converted-trailing-space.md` — the Issue
  #14 trailing-whitespace edge case.
- `docs/research/personal-use-log.md` Entry 2 — first real-world run
  that exercised the full `[Converted]` + trailing-space + 2026
  AppleScript stack end-to-end.
