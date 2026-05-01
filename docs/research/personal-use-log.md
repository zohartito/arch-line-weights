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

---

(Add new entries above this line)

## Roll-up (re-run aggregation script as entries accumulate)

| Drawings logged | Mean success rate | Total hours saved | Decision-ready? |
|---|---|---|---|
| 1 (reference only) | 86% | 5.8 hrs | No — need ≥5 drawings |

## Related

- `docs/ROADMAP.md` Phase A — uses this log as the validation artifact
- `docs/POSTMORTEM.md` Attempt 5 — context for the stubborn-layer issues
- `docs/research/subagent-queue.md` #8 — algorithmic fix for the 3 stubborn layers
