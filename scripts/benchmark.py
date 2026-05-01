#!/usr/bin/env python3
"""Benchmark suite for the arch-line-weights pipeline.

For each input drawing, times the full pipeline:

  1. ``apply-saas`` (B6: stroke-width rewrite only).
  2. ``apply-saas --poche`` (B6 + B7: rewrite + poché injection).
  3. ``apply-jsx`` if Adobe Illustrator + ``osascript`` are available;
     otherwise the run is marked "skipped" and the table column shows ``—``.

Records per run:

  * input bytes / output bytes
  * OCG layer count (from ``inspect_file``)
  * cut-layer count (Rhino ClippingPlaneIntersections shape)
  * polygons injected (poché run only)
  * poché success rate (layers_injected / layers_targeted)

Output:

  * Markdown table appended to ``docs/research/benchmarks.md`` (creates the
    file if it does not exist).
  * Structured JSON dump at ``benchmarks.json`` next to the markdown.

Usage::

    python scripts/benchmark.py --input /tmp/arch-lw-smoke/test.ai --runs 3
    python scripts/benchmark.py --input /path/to/drawings --runs 1
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# Use the public Python API for apply-saas / apply-saas-with-poche so we get
# structured ApplySaasResult / PocheSaasResult diagnostics back, instead of
# parsing CLI stderr.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from arch_line_weights.apply_saas import apply_to_file as apply_saas_to_file
from arch_line_weights.classify import auto_by_luminance
from arch_line_weights.inspect import inspect_file
from arch_line_weights.poche_saas import apply_saas_with_poche
from arch_line_weights.presets import select_preset

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BENCHMARKS_MD = REPO_ROOT / "docs" / "research" / "benchmarks.md"
DEFAULT_BENCHMARKS_JSON = REPO_ROOT / "docs" / "research" / "benchmarks.json"
SUPPORTED_SUFFIXES = (".ai", ".pdf")


@dataclass
class StageTiming:
    """Timing + stats for a single pipeline stage on a single input file."""

    stage: str  # "apply-saas" | "apply-saas --poche" | "apply-jsx"
    times_seconds: list[float] = field(default_factory=list)
    output_bytes: int = 0
    weights_applied: dict[str, int] = field(default_factory=dict)
    polygons_injected: int = 0
    layers_injected: int = 0
    layers_targeted: int = 0
    skipped: bool = False
    skip_reason: str | None = None
    error: str | None = None

    @property
    def median(self) -> float:
        return statistics.median(self.times_seconds) if self.times_seconds else 0.0

    @property
    def best(self) -> float:
        return min(self.times_seconds) if self.times_seconds else 0.0

    @property
    def success_rate(self) -> float:
        if self.layers_targeted == 0:
            return 0.0
        return self.layers_injected / self.layers_targeted


@dataclass
class FileBenchmark:
    """One row in the markdown table — all stages for a single input file."""

    source: str
    input_bytes: int
    layer_count: int
    cut_layer_count: int
    runs: int
    apply_saas: StageTiming
    apply_saas_poche: StageTiming
    apply_jsx: StageTiming


def _count_cut_layers(layer_names: list[str]) -> int:
    """Coarse Rhino ClippingPlaneIntersections count (pre-glass-filter)."""
    needle = "clippingplaneintersections"
    return sum(1 for n in layer_names if needle in n.lower())


def _illustrator_available() -> bool:
    """Return True only if osascript AND the Illustrator app bundle exist.

    The benchmark CLI is meant to be runnable on any developer machine; if
    Illustrator is not installed (CI, Linux, fresh laptop), apply-jsx hangs
    indefinitely waiting for the GUI app. Probe both layers and bail out
    fast in either failure mode.
    """
    if platform.system() != "Darwin":
        return False
    if shutil.which("osascript") is None:
        return False
    # Cheap, deterministic probe: ask LaunchServices whether com.adobe.illustrator
    # is registered. Returns 0 only when the bundle is installed; we cap at 5s
    # so a stuck launchd never blocks the whole benchmark.
    try:
        proc = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Finder" to exists application file id "com.adobe.illustrator"',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return proc.returncode == 0 and proc.stdout.strip().lower() == "true"


def _build_mapping(src: Path) -> dict[tuple[int, int, int], float]:
    """Auto-classify the input's colors into the ``section`` preset tiers.

    Mirrors what ``arch-lw apply-saas --auto`` does internally.
    """
    rep = inspect_file(str(src))
    tiers = select_preset("section", scale="1/4", for_print=False)
    return auto_by_luminance(rep, tiers)


def _time_apply_saas(
    src: Path, runs: int, mapping: dict[tuple[int, int, int], float]
) -> StageTiming:
    """B6 only: time ``apply_to_file`` (no poché)."""
    t = StageTiming(stage="apply-saas")
    last_result = None
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(runs):
            dst = Path(tmp) / f"out_{i}.ai"
            t0 = time.perf_counter()
            try:
                last_result = apply_saas_to_file(str(src), str(dst), mapping)
            except Exception as exc:
                t.error = str(exc)
                return t
            t.times_seconds.append(time.perf_counter() - t0)
        if last_result is not None:
            t.output_bytes = last_result.output_size
            t.weights_applied = {f"{w}": n for w, n in last_result.weights_applied.items()}
    return t


def _time_apply_saas_poche(
    src: Path, runs: int, mapping: dict[tuple[int, int, int], float]
) -> StageTiming:
    """B6 + B7: time ``apply_saas_with_poche``."""
    t = StageTiming(stage="apply-saas --poche")
    last_apply = None
    last_poche = None
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(runs):
            dst = Path(tmp) / f"out_{i}.ai"
            t0 = time.perf_counter()
            try:
                last_apply, last_poche, _report = apply_saas_with_poche(
                    str(src), str(dst), mapping
                )
            except Exception as exc:
                t.error = str(exc)
                return t
            t.times_seconds.append(time.perf_counter() - t0)
        if last_apply is not None:
            t.output_bytes = last_apply.output_size
            t.weights_applied = {
                f"{w}": n for w, n in last_apply.weights_applied.items()
            }
        if last_poche is not None:
            t.polygons_injected = last_poche.polygons_injected
            t.layers_injected = last_poche.layers_injected
            t.layers_targeted = last_poche.layers_targeted
    return t


def _time_apply_jsx(src: Path, runs: int, *, per_run_timeout: int = 300) -> StageTiming:
    """Time ``arch-lw apply-jsx`` if Illustrator/osascript is available.

    apply-jsx drives Illustrator through AppleScript and is by far the
    slowest stage. We cap each run at ``per_run_timeout`` seconds so a
    stuck Illustrator GUI doesn't deadlock the benchmark.
    """
    t = StageTiming(stage="apply-jsx")
    if runs <= 0:
        t.skipped = True
        t.skip_reason = "jsx runs disabled"
        return t
    if not _illustrator_available():
        t.skipped = True
        t.skip_reason = "Adobe Illustrator app not detected"
        return t

    with tempfile.TemporaryDirectory() as tmp:
        for i in range(runs):
            dst = Path(tmp) / f"out_jsx_{i}.ai"
            cmd = [
                "arch-lw",
                "apply-jsx",
                str(src),
                "-o",
                str(dst),
            ]
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=per_run_timeout,
                )
            except subprocess.TimeoutExpired:
                t.skipped = True
                t.skip_reason = (
                    f"apply-jsx exceeded {per_run_timeout}s — Illustrator may be unresponsive"
                )
                return t
            elapsed = time.perf_counter() - t0
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout).strip().splitlines()[-2:]
                t.error = "apply-jsx failed: " + " | ".join(tail)
                t.skipped = True
                t.skip_reason = "apply-jsx returned non-zero (Illustrator missing?)"
                return t
            t.times_seconds.append(elapsed)
            if dst.exists():
                t.output_bytes = dst.stat().st_size
    return t


def benchmark_file(
    src: Path, runs: int, *, jsx_runs: int = 1, jsx_timeout: int = 300
) -> FileBenchmark:
    """Run all three stages on a single input and return the combined result."""
    rep = inspect_file(str(src))
    layer_names = list(rep.layer_names or [])
    mapping = _build_mapping(src)

    return FileBenchmark(
        source=str(src),
        input_bytes=src.stat().st_size,
        layer_count=len(layer_names),
        cut_layer_count=_count_cut_layers(layer_names),
        runs=runs,
        apply_saas=_time_apply_saas(src, runs, mapping),
        apply_saas_poche=_time_apply_saas_poche(src, runs, mapping),
        apply_jsx=_time_apply_jsx(src, jsx_runs, per_run_timeout=jsx_timeout),
    )


def _fmt_seconds(t: StageTiming) -> str:
    if t.skipped:
        return f"skipped ({t.skip_reason})" if t.skip_reason else "skipped"
    if t.error:
        return f"error: {t.error[:60]}"
    if not t.times_seconds:
        return "—"
    return f"{t.median:.2f}s (best {t.best:.2f}s)"


def _fmt_bytes(n: int) -> str:
    return f"{n:,}" if n else "—"


def _markdown_section(
    benchmarks: list[FileBenchmark], started_at: datetime, runs: int
) -> str:
    """One header + one table per benchmark run, appended to benchmarks.md."""
    lines: list[str] = []
    stamp = started_at.strftime("%Y-%m-%d %H:%M:%S %Z")
    lines.append(f"## Run {stamp} (runs={runs})")
    lines.append("")
    lines.append(f"Platform: `{platform.platform()}` — Python {platform.python_version()}")
    lines.append("")
    lines.append(
        "| file | input | layers | cut | apply-saas | apply-saas --poche | "
        "apply-jsx | output (poche) | polygons | success |"
    )
    lines.append(
        "|------|------:|-------:|----:|-----------|--------------------|"
        "----------|---------------:|---------:|--------:|"
    )
    for b in benchmarks:
        name = Path(b.source).name
        lines.append(
            f"| `{name}` "
            f"| {_fmt_bytes(b.input_bytes)} "
            f"| {b.layer_count} "
            f"| {b.cut_layer_count} "
            f"| {_fmt_seconds(b.apply_saas)} "
            f"| {_fmt_seconds(b.apply_saas_poche)} "
            f"| {_fmt_seconds(b.apply_jsx)} "
            f"| {_fmt_bytes(b.apply_saas_poche.output_bytes)} "
            f"| {b.apply_saas_poche.polygons_injected} "
            f"| {b.apply_saas_poche.success_rate * 100:.0f}% |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _append_markdown(
    benchmarks: list[FileBenchmark],
    out_md: Path,
    started_at: datetime,
    runs: int,
) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    section = _markdown_section(benchmarks, started_at, runs)
    if not out_md.exists():
        header = (
            "# arch-line-weights benchmarks\n\n"
            "Auto-generated by `scripts/benchmark.py`. Each section below is one\n"
            "benchmark run; sections accumulate over time so we can spot regressions.\n\n"
            "Stages timed:\n\n"
            "* `apply-saas` — B6 stroke-width rewrite only (no poché)\n"
            "* `apply-saas --poche` — B6 + B7 (rewrite + poché injection)\n"
            "* `apply-jsx` — Illustrator-driven path (skipped if osascript / "
            "Illustrator unavailable)\n\n"
        )
        out_md.write_text(header + section, encoding="utf-8")
    else:
        with out_md.open("a", encoding="utf-8") as fh:
            fh.write("\n" + section)


def _dump_json(
    benchmarks: list[FileBenchmark],
    out_json: Path,
    started_at: datetime,
    runs: int,
) -> None:
    """Always overwrite the JSON dump with the latest run's data.

    The markdown gets appended (so we keep history) but the JSON stays
    machine-readable for the latest run only — keeps downstream tooling
    simple.
    """
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "started_at": started_at.isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "runs": runs,
        "benchmarks": [asdict(b) for b in benchmarks],
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _gather_inputs(arg: Path) -> list[Path]:
    """``--input`` accepts a single file OR a directory of files."""
    if arg.is_file():
        if arg.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise SystemExit(f"unsupported file type: {arg.suffix}")
        return [arg]
    if arg.is_dir():
        return sorted(
            p
            for p in arg.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        )
    raise SystemExit(f"--input not found: {arg}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark the arch-line-weights pipeline."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Single .ai/.pdf file OR directory of files to benchmark.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of timing runs per stage (default 3). apply-jsx uses --jsx-runs.",
    )
    parser.add_argument(
        "--jsx-runs",
        type=int,
        default=1,
        help="Runs for apply-jsx specifically (default 1; each launches Illustrator).",
    )
    parser.add_argument(
        "--jsx-timeout",
        type=int,
        default=300,
        help="Per-run timeout in seconds for apply-jsx (default 300).",
    )
    parser.add_argument(
        "--no-jsx",
        action="store_true",
        help="Skip the apply-jsx stage entirely (faster headless benchmarks).",
    )
    parser.add_argument(
        "--md",
        type=Path,
        default=DEFAULT_BENCHMARKS_MD,
        help="Markdown output path (appended; default docs/research/benchmarks.md).",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=DEFAULT_BENCHMARKS_JSON,
        help="JSON dump path (overwritten; default docs/research/benchmarks.json).",
    )
    args = parser.parse_args(argv)

    inputs = _gather_inputs(args.input)
    if not inputs:
        print(f"no benchmarkable files at {args.input}", file=sys.stderr)
        return 1

    started_at = datetime.now(tz=UTC)
    benchmarks: list[FileBenchmark] = []
    for src in inputs:
        # Skip apparent prior outputs to avoid double-processing.
        upper = src.name.upper()
        if "HIERARCHY" in upper or "POCHE" in upper:
            print(f"  skip {src.name} (looks like an arch-lw output)", file=sys.stderr)
            continue
        print(f"\n=> {src.name}  ({src.stat().st_size:,} bytes)", file=sys.stderr)
        # --no-jsx → force apply-jsx skip without probing osascript/Illustrator
        jsx_runs = 0 if args.no_jsx else args.jsx_runs
        b = benchmark_file(
            src, args.runs, jsx_runs=jsx_runs, jsx_timeout=args.jsx_timeout
        )
        if args.no_jsx:
            b.apply_jsx.skipped = True
            b.apply_jsx.skip_reason = "skipped via --no-jsx"
        benchmarks.append(b)
        for stage in (b.apply_saas, b.apply_saas_poche, b.apply_jsx):
            print(f"   {stage.stage:24s}  {_fmt_seconds(stage)}", file=sys.stderr)

    if not benchmarks:
        print("no benchmarks collected", file=sys.stderr)
        return 1

    # Also dump alongside the requested json path for the cwd-friendly form.
    _append_markdown(benchmarks, args.md, started_at, args.runs)
    _dump_json(benchmarks, args.json, started_at, args.runs)
    cwd_json = Path("benchmarks.json")
    try:
        # Keep a copy at ./benchmarks.json so the CLI example in the docstring
        # works as-advertised when invoked from the repo root.
        if cwd_json.resolve() != args.json.resolve():
            cwd_json.write_text(args.json.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        # The cwd may be read-only (CI); the canonical dump under --json is
        # still authoritative.
        pass

    print(
        f"\nwrote {args.md}\nwrote {args.json}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
