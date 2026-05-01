# apply-jsx UX bugfix notes (2026-05-01)

> Implementation notes for the four `apply-jsx` UX bugs surfaced during
> the first non-section drawing run. See `docs/POSTMORTEM.md` Attempt 9
> for the run that exposed them and `tests/test_apply_jsx_bugs.py` for
> the regression coverage.

## Issue #8 — JSX progress heartbeat

**Problem:** v0.5.1 `apply-jsx` ran silently for 60+ minutes on a 98 MB
drawing with no progress signal and no hang detection.

**Fix:** the JSX now writes one heartbeat line per layer to
`/tmp/arch_lw_jsx_progress.txt`:

```
1/52: axon::Visible::Curves::FLOOR_DATUMS (412 paths)
2/52: axon::Visible::Curves::TEC_TIMBER (1,883 paths)
...
DONE
```

The Python side runs a `_HeartbeatPoller` daemon thread that polls
every 2 s, prints new lines to stderr, and surfaces a one-time warning
when the heartbeat goes stale for >5 min. Per the issue spec the
warning is informational only — the user, not the wrapper, decides
whether Illustrator is hung enough to abort. The poller exits on the
literal `DONE` line.

The completion ritual: JSX always writes `DONE` even on exception, so
the poller drains cleanly in either case.

**Why threading and not asyncio?** `subprocess.run(["osascript", ...])`
already blocks the main thread. A daemon `threading.Thread` reading
the heartbeat file is the simplest concurrent reader without
restructuring the call site.

**Gotcha hit during implementation:** never name a `threading.Thread`
subclass attribute `self._stop`. Python's thread internals look up
`self._stop()` as a callable cleanup hook, and a `threading.Event`
shadowed at that name causes `TypeError: 'Event' object is not callable`
when the thread is joined. Renamed to `self._stop_event`.

## Issue #10 — `[Converted]` doc-state detection

**Problem:** when Illustrator has a non-AI source (older `.ai`, PDF)
open as `<basename> [Converted]`, AppleScript `tell ... open POSIX
file` returns silently without actually opening the disk file. The
JSX then can't find its target document by `fullName.fsName` and
fails with `ERROR: target doc not open`.

**Fix:** two-pronged.

1. **Pre-flight active-doc query** via AppleScript:
   ```applescript
   tell application "Adobe Illustrator"
     set docName to name of active document
     set docPath to POSIX path of (file path of active document)
     return docName & "|" & docPath
   end tell
   ```
   The wrapper checks whether `docName` ends with `[Converted]` and
   whether the basename matches the requested `src`.

2. **Operate on open doc** when the active doc IS the right file in
   `[Converted]` state — pass `USE_OPEN_DOC=true` into the JSX, which
   then skips the `fullName` lookup and uses `app.activeDocument`
   directly. This is the better UX path: no second `open` call, no
   race window, works whether the doc has been saved-as yet or not.

3. **Clear error otherwise:** if there's a `[Converted]` doc whose
   basename doesn't match the requested `src`, the wrapper raises
   `RuntimeError` with the exact message in the issue spec
   (`"Illustrator has '<name> [Converted]' open. Save it (Cmd+S) and
   close the original to allow apply-jsx to open the disk file
   fresh, or close the [Converted] doc entirely."`).

The `_is_converted_match` helper handles the four common name shapes:
`<basename>.ai → <basename> [Converted]`,
`<basename>.ai → <basename> [Converted].ai`, and the `<stem>` variants.

## Issue #11 — configurable `--timeout`

**Problem:** the v0.5.1 hardcoded 60-min `with timeout of 3600 seconds`
was wrong both ways: too long for small files (waste a full hour on a
hang) and too short for big ones (false abort when the JSX is still
making progress).

**Fix:** new `--timeout MINUTES` flag plumbed all the way through to
the `osascript with timeout of N seconds` line. Default 30 (down from
60), max 240 (clamped via `click.IntRange`). Honors the
`ARCH_LW_JSX_TIMEOUT_MIN` env var when the flag is omitted.

`resolve_timeout_minutes(timeout_min: int | None)` is the single
resolution point — explicit arg wins, then env var, then
`DEFAULT_TIMEOUT_MIN`. Garbage env values fall back silently. Final
value is clamped to `[1, MAX_TIMEOUT_MIN]`.

## Issue #13 — `--preset` flag wire-up

**Problem:** `apply-saas` had `--preset {section|plan|elevation|detail}`
since v0.5; `apply-jsx` did not. For non-section drawings via JSX,
users had no way to pick the right tier ladder — the embedded
classifier always emitted the section weights (cut=1.0, profile=0.5,
…), which over-weights plans by 1 ISO step and elevations by their
silhouette tier.

**Fix:** `as_jsx_function()` now accepts `preset`, `scale`, and
`for_print` kwargs. When `preset` is one of the four family names,
the emitted JS uses weights from
`tier_weights_for_preset(preset, scale, for_print)` instead of the
classifier's stock per-tier values.

`tier_weights_for_preset()` cross-walks the classifier's tier names
(`cut`, `structure_primary`, `frames`, …) to the preset's tier names
(`walls_cut`, `casework`, `furniture`, …) and pulls the weight from
`select_preset()`. The cross-walk is hand-tuned per preset (see
`_RHINO_TIER_TO_PRESET_TIER` in `layer_classify.py`). Tiers without
a preset analog keep the classifier's stock weight.

Cross-walk sketch (`cut` row, screen weights):

| classifier tier      | section | plan      | elevation  | detail        |
|----------------------|---------|-----------|------------|---------------|
| `cut`                | cut 1.0 | walls_cut 0.71 | silhouette 1.0 | cut_primary 1.5 |
| `structure_primary`  | profile 0.5 | casework 0.5 | profile 0.71 | cut_secondary 1.0 |

Default behaviour: `preset=None` keeps every weight at the v0.5.1 hardcoded
values. The CLI default is `--preset section`, which produces output
identical to v0.5.1 for section drawings (the cross-walk is calibrated to
preserve the existing weights for that case).

## Synthetic heartbeat test

`test_heartbeat_poller_picks_up_appended_lines` proves the polling
contract: a synthetic heartbeat file gets written line by line in
the same shape the JSX would produce, and the poller picks up each
line, prints it through the injected `printer=` callback, and exits
on `DONE`. The companion test `test_heartbeat_poller_emits_stale_warning`
proves the >5-min staleness detection (parameterised down to 0.3 s
so the test runs fast). Both verify the no-abort contract.
