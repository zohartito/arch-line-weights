#!/usr/bin/env python3
"""Self-correcting iteration loop around the deterministic visual judge.

One command turns "apply → look → tweak overrides → re-apply" into a loop:

  1. run the pipeline (default ``arch-lw apply-saas <src> --architectural --poche
     --poche-overrides <overrides> --report-json <report> -o <out>``),
  2. render the result and score it with ``scripts/visual_judge.py``,
  3. if the verdict is ``review``, merge the judge's ``suggested_overrides`` into
     the overrides JSON and go again — up to ``--iterations`` times.

Each iteration writes a run-log JSON so the whole trail is inspectable.

The bake caveat (read this)
---------------------------
``apply-saas`` rewrites the *native Illustrator payload* headlessly. Those edits
are **not visible in the live PDF content stream** until Illustrator re-bakes the
file (open + Save As). So rendering the raw ``apply-saas`` output under-reports the
hierarchy — on the real hero, pre-bake ``section-v4 POCHE.ai`` scores 1.41:1
(weight-flatness) while the Illustrator-baked ``section-v4-BAKED.ai`` scores
5.56:1. Therefore:

  * Pass ``--baked-after <file>`` with an Illustrator-baked render/file whenever
    you can — that is what the judge should see, and the loop scores it directly.
  * Without ``--baked-after`` the loop scores the raw pipeline output and prints a
    loud caveat; treat a low hierarchy_spread there as "un-baked", not "flat".

An automated Illustrator bake step is intentionally OFF by default (it needs a
GUI Illustrator + osascript and is not headless-safe); wire it in via
``--bake-cmd`` if you have it, otherwise supply ``--baked-after``.

Usage::

    python scripts/judge_loop.py "section-raw.ai" \
        --overrides overrides.json --baked-after "section-v4-BAKED.ai" \
        --run-dir runs/ --iterations 3
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import visual_judge as vj  # noqa: E402

DEFAULT_PIPELINE = (
    'arch-lw apply-saas "{src}" --architectural --poche '
    '--poche-overrides "{overrides}" --report-json "{report}" -o "{out}"'
)


def merge_overrides(current: dict[str, Any], suggested: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Merge judge ``suggested_overrides`` into the overrides dict.

    Returns (merged, changed). A suggestion only counts as a change when it adds
    a layer or alters an existing layer's strategy — so the loop can detect a
    fixpoint (no new suggestions) and stop early.
    """
    merged = dict(current)
    changed = False
    for layer, spec in suggested.items():
        if merged.get(layer) != spec:
            merged[layer] = spec
            changed = True
    return merged, changed


def _run_pipeline(template: str, *, src: Path, overrides: Path, out: Path, report: Path) -> dict[str, Any]:
    cmd = template.format(src=src, overrides=overrides, out=out, report=report)
    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def run_loop(
    src: str | Path,
    *,
    overrides_path: str | Path,
    run_dir: str | Path,
    baked_after: str | Path | None = None,
    pipeline: str = DEFAULT_PIPELINE,
    bake_cmd: str | None = None,
    iterations: int = 3,
    dpi: int = 110,
) -> dict[str, Any]:
    src = Path(src)
    overrides_path = Path(overrides_path)
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    overrides: dict[str, Any] = {}
    if overrides_path.exists():
        overrides = json.loads(overrides_path.read_text())

    history: list[dict[str, Any]] = []
    verdict = "review"
    for it in range(1, iterations + 1):
        out_path = run_dir / f"iter-{it}-out{src.suffix}"
        report_path = run_dir / f"iter-{it}-report.json"
        overrides_path.write_text(json.dumps(overrides, indent=2) + "\n")

        pipe = _run_pipeline(pipeline, src=src, overrides=overrides_path, out=out_path, report=report_path)

        # Optional headless bake (off by default; needs GUI Illustrator).
        after = Path(baked_after) if baked_after else out_path
        bake_info: dict[str, Any] | None = None
        if bake_cmd and not baked_after:
            baked_path = run_dir / f"iter-{it}-baked{src.suffix}"
            bcmd = bake_cmd.format(src=out_path, out=baked_path)
            bproc = subprocess.run(shlex.split(bcmd), capture_output=True, text=True)
            bake_info = {"cmd": bcmd, "returncode": bproc.returncode}
            if baked_path.exists():
                after = baked_path

        report_arg = report_path if report_path.exists() else None
        try:
            result = vj.judge(after, before=src, report_json=report_arg, dpi=dpi)
        except Exception as exc:  # rendering / judging failed — record and stop
            entry = {"iteration": it, "pipeline": pipe, "judge_error": repr(exc), "after": str(after)}
            (run_dir / f"iter-{it}.json").write_text(json.dumps(entry, indent=2) + "\n")
            history.append(entry)
            verdict = "error"
            break

        stream_visible_warning = None
        if not baked_after and not bake_cmd:
            stream_visible_warning = (
                "Scored the raw pipeline output — apply-saas payload edits are not in the "
                "live PDF stream until Illustrator re-bakes. Pass --baked-after for a true score."
            )

        entry = {
            "iteration": it,
            "pipeline": pipe,
            "bake": bake_info,
            "after_scored": str(after),
            "overrides_used": overrides,
            "verdict": result["verdict"],
            "scores": result["scores"],
            "why": result["why"],
            "suggested_overrides": result["suggested_overrides"],
            "stream_visible_warning": stream_visible_warning,
        }
        (run_dir / f"iter-{it}.json").write_text(json.dumps(entry, indent=2) + "\n")
        history.append(entry)

        verdict = result["verdict"]
        if verdict == "pass":
            break
        overrides, changed = merge_overrides(overrides, result["suggested_overrides"])
        if not changed:
            entry["stopped"] = "no new overrides suggested (fixpoint) — manual step needed"
            (run_dir / f"iter-{it}.json").write_text(json.dumps(entry, indent=2) + "\n")
            break

    summary = {
        "src": str(src),
        "iterations_run": len(history),
        "final_verdict": verdict,
        "overrides_path": str(overrides_path),
        "run_dir": str(run_dir),
        "final_scores": history[-1]["scores"] if history and "scores" in history[-1] else None,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Self-correcting visual-judge iteration loop.")
    p.add_argument("src", help="Source drawing (.ai/.pdf) fed to the pipeline")
    p.add_argument(
        "--overrides", required=True, help="Poché overrides JSON (created if absent, updated in place)"
    )
    p.add_argument("--run-dir", required=True, help="Directory for per-iteration run logs and outputs")
    p.add_argument("--baked-after", default=None, help="Illustrator-baked result to score (recommended)")
    p.add_argument(
        "--pipeline",
        default=DEFAULT_PIPELINE,
        help="Pipeline command template ({src}{overrides}{out}{report})",
    )
    p.add_argument(
        "--bake-cmd", default=None, help="Optional bake command template ({src}{out}); off by default"
    )
    p.add_argument("--iterations", type=int, default=3, help="Max iterations")
    p.add_argument("--dpi", type=int, default=110, help="Render dpi for the judge")
    args = p.parse_args(argv)

    summary = run_loop(
        args.src,
        overrides_path=args.overrides,
        run_dir=args.run_dir,
        baked_after=args.baked_after,
        pipeline=args.pipeline,
        bake_cmd=args.bake_cmd,
        iterations=args.iterations,
        dpi=args.dpi,
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["final_verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
