#!/usr/bin/env python3
"""Eval gate: benchmark the committed synthetic fixture, diff vs the committed baseline.

Runs ``scripts/benchmark.py`` on ``tests/fixtures/eval/synthetic-cut.ai``
(``--runs 1 --no-jsx``) and compares the *deterministic* quality metrics of each
stage against ``benchmarks/ci-baseline.json``:

  gated (must match exactly): weights_applied, polygons_injected,
      layers_injected, layers_targeted, skipped, error
  info-only (reported, never gated): output_bytes, median seconds — these vary
      by platform/library version and are not quality signals.

Exit codes: 0 = all gated metrics match baseline · 1 = regression (or missing
baseline) · 2 = benchmark itself failed to run.

Usage::

    python scripts/eval_gate.py                        # compare, gate
    python scripts/eval_gate.py --report delta.md      # also write markdown delta
    python scripts/eval_gate.py --update-baseline      # record current as baseline
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "eval" / "synthetic-cut.ai"
BASELINE = REPO_ROOT / "benchmarks" / "ci-baseline.json"
STAGES = ("apply_saas", "apply_saas_poche")
GATED_KEYS = ("weights_applied", "polygons_injected", "layers_injected", "layers_targeted", "skipped", "error")


def run_benchmark() -> dict:
    """Run benchmark.py on the fixture; return the parsed JSON dump."""
    with tempfile.TemporaryDirectory() as tmp:
        json_path = Path(tmp) / "bench.json"
        md_path = Path(tmp) / "bench.md"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "benchmark.py"),
            "--input", str(FIXTURE),
            "--runs", "1",
            "--no-jsx",
            "--json", str(json_path),
            "--md", str(md_path),
        ]
        # cwd=tmp: benchmark.py drops a courtesy copy at ./benchmarks.json in
        # its cwd — keep that out of the repo checkout.
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp)
        if proc.returncode != 0 or not json_path.exists():
            print(f"benchmark failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
            sys.exit(2)
        return json.loads(json_path.read_text())


def median_seconds(stage: dict) -> float:
    times = stage.get("times_seconds") or []
    return statistics.median(times) if times else 0.0


def compare(baseline: dict, current: dict) -> tuple[list[str], list[str], int, int]:
    """Return (markdown lines, regression descriptions, matched, total)."""
    lines = [
        "| stage | metric | baseline | current | gate |",
        "| --- | --- | --- | --- | --- |",
    ]
    regressions: list[str] = []
    matched = 0
    total = 0
    base_by_stage = {s: baseline["benchmarks"][0][s] for s in STAGES}
    curr_by_stage = {s: current["benchmarks"][0][s] for s in STAGES}
    for stage in STAGES:
        base, curr = base_by_stage[stage], curr_by_stage[stage]
        for key in GATED_KEYS:
            total += 1
            ok = base.get(key) == curr.get(key)
            matched += ok
            if not ok:
                regressions.append(f"{stage}.{key}: baseline={base.get(key)!r} current={curr.get(key)!r}")
            lines.append(
                f"| {stage} | {key} | `{base.get(key)!r}` | `{curr.get(key)!r}` | {'✅' if ok else '❌'} |"
            )
        lines.append(
            f"| {stage} | output_bytes (info) | {base.get('output_bytes')} | {curr.get('output_bytes')} | — |"
        )
        lines.append(
            f"| {stage} | median s (info) | {median_seconds(base):.3f} | {median_seconds(curr):.3f} | — |"
        )
    return lines, regressions, matched, total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-baseline", action="store_true", help="Record current run as the baseline.")
    parser.add_argument("--report", type=Path, default=None, help="Write the markdown delta report here.")
    args = parser.parse_args()

    current = run_benchmark()

    if args.update_baseline:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(current, indent=2) + "\n")
        print(f"baseline written: {BASELINE}")
        return 0

    if not BASELINE.exists():
        print(f"no baseline at {BASELINE} — run with --update-baseline first")
        return 1

    baseline = json.loads(BASELINE.read_text())
    lines, regressions, matched, total = compare(baseline, current)
    score = 100.0 * matched / total
    verdict = "PASS" if not regressions else "FAIL"
    header = (
        f"## Eval gate: {verdict} — score {score:.0f}% ({matched}/{total} gated metrics match baseline)\n\n"
        f"Fixture: `{FIXTURE.relative_to(REPO_ROOT)}` · baseline: `{BASELINE.relative_to(REPO_ROOT)}` "
        f"(recorded {baseline.get('started_at', '?')})\n"
    )
    report = header + "\n" + "\n".join(lines) + "\n"
    if regressions:
        report += "\n**Regressions:**\n" + "\n".join(f"- `{r}`" for r in regressions) + "\n"

    print(report)
    if args.report:
        args.report.write_text(report)

    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
