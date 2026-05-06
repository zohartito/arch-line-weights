# Personal-use log — Phase A validation

> Phase A goal: prove the tool works on real drawings beyond the
> reference one. Each drawing run goes here. Aggregate at term end to
> decide whether to advance to Phase B.

## Aggregation script

Run after adding entries to roll up metrics:

```python
# scripts/personal_use_aggregate.py
import re, statistics, sys
from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "docs/research/personal-use-log.md"
text = LOG.read_text()

entries = re.findall(
    r"### Entry \d+.*?(?=### Entry \d+|\Z)", text, re.DOTALL
)

def field(entry, name, cast=str):
    m = re.search(rf"- \*\*{name}\*\*: (.+)", entry)
    if not m: return None
    val = m.group(1).strip()
    try: return cast(val.split()[0])
    except Exception: return val

cut_success = [field(e, "Cut layers polygonized cleanly", int) for e in entries]
cut_total = [field(e, "Cut layers total", int) for e in entries]
manual_fixes = [field(e, "Manual fixes needed", int) for e in entries]
hours_saved = [field(e, "Estimated hours saved vs manual", float) for e in entries]

print(f"Entries: {len(entries)}")
if cut_success and cut_total:
    rate = [s/t for s, t in zip(cut_success, cut_total) if s and t]
    print(f"Mean cut-layer success rate: {statistics.mean(rate):.1%}")
if manual_fixes:
    valid = [m for m in manual_fixes if m is not None]
    print(f"Mean manual fixes per drawing: {statistics.mean(valid):.1f}")
if hours_saved:
    valid = [h for h in hours_saved if h is not None]
    print(f"Total hours saved across all drawings: {sum(valid):.1f}")
```

## Decision gate (end of Phase A)

- ✅ Advance to Phase B if: mean cut-layer success rate ≥85% across
  ≥5 drawings, AND total hours saved ≥10 hours, AND zohar prefers
  the tool to manual work
- ⚠️ Iterate on tool if: success rate <85% — focus E1 work on the
  failing patterns
- ❌ Shelve if: tool is too painful to use for personal work — the
  market won't tolerate what the founder won't

## Entry template

Copy this for each new drawing run:

```markdown
### Entry N — YYYY-MM-DD — <drawing-name>

- **Source file**: `<path>`
- **File size MB**: 
- **Stroke count**:
- **OCG layer count**:
- **Cut layers total**: 
- **Cut layers polygonized cleanly**: 
- **Cut layers needing __POCHE_CLOSE__**: 
- **Cut layers fully failed**: 
- **Hierarchy preset used**: section / plan / elevation / detail
- **Scale flag**: 1/16 / 1/8 / 1/4 / 1/2
- **Print flag**: yes / no
- **Estimated manual time it would have taken**: __ hrs
- **Actual time spent (incl. CLI runtime + manual fixes)**: __ hrs
- **Estimated hours saved vs manual**: __ hrs
- **Manual fixes needed**: __  (count and 1-line each)
- **What worked well**:
- **What didn't work / what surprised me**:
- **What I'd add to the tool because of this**:
- **Decision**: ✅ tool good enough / ⚠️ needs fix before next drawing / ❌ blocker
```

## Entries

### Entry 0 — 2026-04-30 — `DRAWING 4 SECTION [Converted].ai` (reference drawing)

- **Source file**: `/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/DRAWING 4 SECTION [Converted].ai`
- **File size MB**: 24
- **Stroke count**: 340,323
- **OCG layer count**: 62
- **Cut layers total**: 21
- **Cut layers polygonized cleanly**: 18 (with auto-bridge)
- **Cut layers needing __POCHE_CLOSE__**: 0 (not yet user-applied)
- **Cut layers fully failed**: 3 (`23_WINDOW_FRAMES_REMAP`, `26_CLT_GAP_ROOF_CAP`, `11_CU_CORR_SOLID_OPAQUE`)
- **Hierarchy preset used**: section
- **Scale flag**: (default — screen review)
- **Print flag**: no
- **Estimated manual time it would have taken**: ~6 hrs (62 layers × ~5 min each)
- **Actual time spent (incl. CLI runtime + manual fixes)**: ~11 min CLI + 0 min manual = ~11 min
- **Estimated hours saved vs manual**: ~5.8 hrs
- **Manual fixes needed**: 0 (3 stubborn layers were left as-is, deferred to Phase E1)
- **What worked well**:
  - Layer fidelity: 62/62 layers preserved
  - Auto-bridge rescued 4 layers that bare linemerge missed
  - Stroke weights look right at on-screen review zoom
- **What didn't work / what surprised me**:
  - 3 cut layers couldn't be polygonized — needs algorithmic improvement
  - Source doc became dirty after `saveAs`; had to manually close-and-reopen
- **What I'd add to the tool because of this**:
  - Confidence flag in CLI output for low-confidence fills
  - Per-layer override JSON
  - Auto-close source after `saveAs` to prevent tab confusion
- **Decision**: ⚠️ needs fix before next drawing (3 stubborn layers) BUT good enough to use on simpler drawings now

### Entry 1 — 2026-05-01 — `macro.ai` (ARCH 211 urban-scale plan)

- **Source file**: `/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 211/macro.ai` (eventually saved-as `macro_for_archlw.ai`)
- **File size MB**: 98 (saved version; original was 237 MB)
- **Stroke count**: ~1.25M (565K + 617K + smaller buckets per inspect output)
- **OCG layer count**: not enumerated (apply-saas pipeline doesn't list them; would be in inspect)
- **Cut layers total**: N/A — not a section drawing
- **Cut layers polygonized cleanly**: N/A
- **Cut layers needing __POCHE_CLOSE__**: N/A
- **Cut layers fully failed**: N/A
- **Hierarchy preset used**: **plan** (first non-section validation!)
- **Scale flag**: default (1/4)
- **Print flag**: no (screen weights)
- **Estimated manual time it would have taken**: ~3-4 hours (1.25M strokes × 50 distinct colors at ~5 min per color manually)
- **Actual time spent (incl. CLI runtime + manual fixes)**: ~5 min CLI + 0 min manual = ~5 min
- **Estimated hours saved vs manual**: ~3-4 hrs
- **Manual fixes needed**: 0 (output is clean; user opened in Illustrator post-run)
- **What worked well**:
  - **First successful headless run on a real non-section drawing**
  - Plan preset (PLAN_ISO_SCREEN ladder) applied: 0.18 / 0.25 / 0.35 / 0.50 / 0.71 pt
  - Auto color classifier handled 50 distinct stroke colors → 50 width ops, all tiered correctly
  - Layer fidelity preserved (PieceInfo intact)
  - Output 72.8 MB (smaller than input due to zstd recompression)
  - Pure-Python: zero Illustrator dependency for the actual work
- **What didn't work / what surprised me**:
  - **`apply-saas` first attempt failed on 237 MB original** — PyMuPDF couldn't open `inspect_file()`. Required user to first save-as a smaller version (98 MB) via Illustrator.
  - **`apply-jsx` failed twice** on the same file — Illustrator had it open as `[Converted]` and AppleScript `tell ... open` returned silently without actually opening the disk file. Then on retry hit the 60-min osascript timeout while Illustrator kept grinding indefinitely (forced-quit eventually).
  - **No progress feedback during long JSX runs** — already filed as Issue #8.
  - **CLI inconsistency**: `apply-jsx` doesn't have `--preset` flag while `apply-saas` does.
- **What I'd add to the tool because of this**:
  - Replace PyMuPDF inspect with pikepdf-based inspect for `.ai` files (PyMuPDF stays for `.pdf` only)
  - Detect `[Converted]` Illustrator state in `apply-jsx` and fail with clear message + suggestion
  - Make JSX timeout configurable; add JSX heartbeat to detect hangs vs progress (Issue #8)
  - Add `--preset` to `apply-jsx` for parity with `apply-saas`
  - Different default output paths for `apply-jsx` (`HIERARCHY-jsx.ai`) vs `apply-saas` (`HIERARCHY-saas.ai`) to prevent overwrite races
- **Decision**: ✅ **tool good enough for plan drawings via `apply-saas`** — major win. ⚠️ apply-jsx path has rough edges that need fixing before it's reliable on large files.

### Entry 2 — 2026-05-05 — `wall section iso cut .ai` (ARCH 211 wall section, trailing-space disk name)

- **Source file**: `/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 211/wall section iso cut .ai` (note literal trailing space before `.ai`)
- **File size MB**: 12.6
- **Stroke count**: not enumerated (apply-jsx path; classifier ran on layer names, not strokes)
- **OCG layer count**: ~30 leaf layers classified by the semantic classifier
- **Cut layers total**: N/A (handled implicitly by classifier; no separate poché run)
- **Cut layers polygonized cleanly**: N/A
- **Cut layers needing __POCHE_CLOSE__**: N/A
- **Cut layers fully failed**: N/A
- **Hierarchy preset used**: **section** (wall section drawing, iso-cut)
- **Scale flag**: default
- **Print flag**: no (screen weights)
- **Estimated manual time it would have taken**: ~2 hrs (wall-section detail, ~30 layers × ~4 min per layer)
- **Actual time spent (incl. CLI runtime + manual fixes)**: ~2 min CLI + 0 min manual = ~2 min
- **Estimated hours saved vs manual**: ~2 hrs
- **Manual fixes needed**: 0
- **Pipeline used**: `apply-jsx --preset section` against the open `[Converted]` doc (corrupt disk file forced the JSX path; pikepdf could not open the trailer-corrupt source).
- **Output**: `wall section iso cut  HIERARCHY-jsx.ai` (3.79 MB; note Issue #12 suffix `HIERARCHY-jsx`)
- **Tier breakdown** (full per-layer dump in `/private/tmp/claude-501/tasks/b6ljidqr4.output`):
  - 1.0 pt — section-cut tier
  - 0.5 pt — primary structural profile
  - 0.35 pt — secondary profile / frames
  - 0.30 pt — minor profile
  - 0.18 pt — texture / hatching
  - 0.13 pt — hairline / annotation
- **What worked well**:
  - **`[Converted]` state detection engaged correctly** — the v0.6.4 AppleScript fix (`current document` + `(get name of …)`) resolved Illustrator 2026 build 30.x's `name`-property/class ambiguity, and the v0.6.3 trailing-whitespace normalization in `_is_converted_match` handled `wall section iso cut  [Converted].ai` → `wall section iso cut .ai` correctly.
  - Wrapper printed the `# detected [Converted] doc … operating on the open document directly (Issue #10)` line and skipped the brittle `open POSIX file` step.
  - Semantic classifier hit ~30 leaf layers and tiered them across the 6-step ladder cleanly.
  - Output saved with the new `HIERARCHY-jsx` suffix (Issue #12 fix), so it doesn't collide with any future `apply-saas` run on the same source.
  - Heartbeat poller (Issue #8) printed per-layer progress; no stale-warning fired.
- **What didn't work / what surprised me**:
  - **Original disk file is trailer-corrupt** — `pikepdf.open()` raised on `wall section iso cut .ai`; same root cause as `macro.ai` in Entry 1. The headless pure-Python path (`apply-saas`) is NOT a fallback when the source is structurally broken at the PDF trailer. Required Illustrator Save-As workaround would have produced a clean 12 MB version, but since Illustrator already had the file open as `[Converted]`, the JSX path operated on the in-memory doc instead — convenient but circumstantial.
  - The trailing-space disk filename is a real-world artifact of Rhino's exporter (a layer name ending in space leaks into the export filename). Issue #14 fixed this for the matcher but the source-file-corruption gap remains.
- **What I'd add to the tool because of this**:
  - Detect trailer-corrupt `.ai` files in `apply-saas` and surface a clear "Open in Illustrator and Save As, or use `apply-jsx` against the open doc" message instead of the raw pikepdf traceback.
  - Per-layer tier breakdown could be persisted next to the output (e.g. `<output>.tiers.json`) instead of only living in the JSX report file.
- **Decision**: ✅ **`apply-jsx` is now reliable on real corrupt-source drawings** thanks to the v0.6.1 / v0.6.3 / v0.6.4 issue cluster. The `[Converted]` + trailing-space + AppleScript-syntax fixes all engaged correctly on a real drawing for the first time.

### Entry 3 — 2026-05-05 — `iso axon section  [Converted].ai` (ARCH 202B axon section)

- **Source file**: `/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/iso axon section  [Converted].ai`
- **File size MB**: 43.9
- **Stroke count**: 63 stroke-color/width rewrite ops in the AI private payload
- **OCG layer count**: 62
- **Cut layers total**: 8 semantically structural poché targets under `--architectural`
- **Cut layers polygonized cleanly**: 8/8 injected, but visual quality is partial
- **Cut layers needing __POCHE_CLOSE__**: likely 3-5 ambiguous faces (roof, court/backup wall, foundation/concrete returns)
- **Cut layers fully failed**: 0 runtime failures; visual completeness still fails the drawing-quality bar
- **Hierarchy preset used**: section + `--architectural`
- **Scale flag**: default
- **Print flag**: no
- **Estimated manual time it would have taken**: ~3-4 hrs
- **Actual time spent (incl. CLI runtime + manual fixes)**: ~1 min CLI runtime + manual review/fix still needed
- **Estimated hours saved vs manual**: not counted yet; poché still needs human cleanup
- **Manual fixes needed**: structural wall/roof/foundation faces still need review; visible structural candidate fill produced false blobs in experiment
- **Pipeline used**: `apply-saas --auto --architectural --preset section --poche --bridge-strategy=best`
- **Output**: best current candidate is
  `iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0616-current-best.ai`
- **What worked well**:
  - `35 colors mapped`; the earlier `0 colors mapped` symptom is fixed by RGB/CMYK private-payload inspection and architectural mode.
  - `bridge-best` did not hang; per-layer runtime budget kept the run bounded.
  - Semantic architectural hierarchy kept glass, cladding, connectors, and facade screens out of black poché.
  - v0.6.11 helper-assisted structural closure injected 51 polygons across 8/8 structural cut layers.
  - v0.6.12/v0.6.13 rejected helper-only Make2D completion blobs and removed
    the lower-left concrete-base over-expansion.
  - `ARCH_LW_POCHE_OVERLAY=1` created a top `ARCH_LW_POCHE` layer for review.
  - Secondary steel and connector hardware were quieted in the architectural
    section-screen hierarchy.
- **What didn't work / what surprised me**:
  - The output still reads too much like heavy cut bands instead of continuous poché mass.
  - Some real cut solids appear only in `Visible::Curves` / `Visible::Tangents`, not in `ClippingPlaneIntersections`.
  - Filling visible structural layers wholesale recovers missing mass but creates obvious false black blobs, so the tool needs an approval/report workflow before using that evidence aggressively.
  - The overlay layer proves some white stripes were draw-order related, but
    the bigger issue is still incomplete component topology.
- **What I'd add to the tool because of this**:
  - General Make2D completion/component graph shared by line weights and poché.
  - Per-layer architectural review report with target layer, semantic role, helper layers used, skipped visible structural candidates, inferred closure edges, confidence, and user-facing warnings.
  - A deadline-oriented manual mask/closure workflow for ambiguous faces.
  - Illustrator/Computer Use visual QA script to attach screenshots and mark known failure zones after every real run.
- **Decision**: ⚠️ **use hierarchy now; use poché cautiously.** The engine is safer and faster, but this drawing still needs manual poché cleanup before pin-up/print quality.

---

(Add new entries above this line)

## Roll-up (re-run aggregation script as entries accumulate)

| Drawings logged | Drawing types | Headless success | Hours saved | Decision-ready? |
|---|---|---|---|---|
| 4 (reference + macro + wall-section + iso axon) | section, plan, section-iso, axon-section | 4/4 pipelines ran; 3/4 visually acceptable without major manual poché cleanup | ~11 hrs + pending iso cleanup | No — need ≥5 drawings |

## Related

- `docs/ROADMAP.md` Phase A — uses this log as the validation artifact
- `docs/POSTMORTEM.md` Attempt 5 — context for the stubborn-layer issues
- `docs/research/subagent-queue.md` #8 — algorithmic fix for the 3 stubborn layers
