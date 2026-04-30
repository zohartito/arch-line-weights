"""GhPython 3 component: arch-lw hierarchy applier.

Drop into a GHPython component (right-click → Runtime: Python 3 (CPython)),
then wire the inputs/outputs listed below.

Inputs (all Item access except `run`):
  pdf_path     : str   - full path to .ai or .pdf
  mode         : str   - 'layer' | 'color' | 'poche'        (default 'layer')
  preset       : str   - 'section'|'plan'|'elevation'|'detail' (default 'section')
  scale        : str   - e.g. '1/4', '1/8', '1/2'           (default '1/4')
  for_print    : bool  - print-scale ISO 128 weights        (default False)
  mapping_file : str   - path to JSON tier overrides        (optional)
  run          : bool  - trigger                            (default False)

Outputs:
  out_path : str
  report   : str
  success  : bool

Docs: https://developer.rhino3d.com/guides/scripting/scripting-gh-python/
"""
import os
import shutil
import subprocess
from pathlib import Path

TIMEOUT_SEC = 30 * 60


def _resolve_cli():
    exe = "arch-lw.exe" if os.name == "nt" else "arch-lw"
    found = shutil.which(exe)
    if found:
        return found
    candidates = []
    if os.name == "nt":
        candidates += [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "arch-lw" / exe,
            Path("C:/Program Files/arch-lw") / exe,
        ]
    else:
        candidates += [
            Path("/usr/local/bin") / exe,
            Path("/opt/homebrew/bin") / exe,
            Path.home() / ".local" / "bin" / exe,
            Path.home() / ".pyenv" / "shims" / exe,
        ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def _derive_out(src, mode):
    p = Path(src)
    suffix = "POCHE" if mode == "poche" else "HIERARCHY"
    return str(p.with_name(f"{p.stem} {suffix}{p.suffix}"))


def run_arch_lw(pdf_path, mode, preset, scale, for_print, mapping_file):
    cli = _resolve_cli()
    if not cli:
        raise RuntimeError(
            "arch-lw not found on PATH. Install from "
            "https://github.com/zohartito/arch-line-weights or set PATH."
        )
    if not pdf_path or not Path(pdf_path).exists():
        raise FileNotFoundError("Input file not found: " + repr(pdf_path))
    sub = "poche" if mode == "poche" else "apply-jsx"
    out_path = _derive_out(pdf_path, mode)
    cmd = [cli, sub, pdf_path, "--out", out_path]
    if mode != "poche":
        cmd += ["--preset", preset, "--scale", scale]
        if for_print:
            cmd.append("--for-print")
        if mapping_file:
            if not Path(mapping_file).exists():
                raise FileNotFoundError("Mapping JSON not found: " + repr(mapping_file))
            cmd += ["--mapping", mapping_file]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=TIMEOUT_SEC, check=False,
        )
    except subprocess.TimeoutExpired as te:
        raise RuntimeError("arch-lw exceeded {}s; aborted.".format(TIMEOUT_SEC))
    report = (proc.stderr or "") + ("\n--- stdout ---\n" + proc.stdout if proc.stdout else "")
    if proc.returncode != 0:
        raise RuntimeError("arch-lw exit {}\n{}".format(proc.returncode, report))
    return out_path, report


# --- GH component body ---
out_path = ""
report = ""
success = False

if run:
    try:
        out_path, report = run_arch_lw(
            pdf_path,
            (mode or "layer").lower(),
            (preset or "section").lower(),
            scale or "1/4",
            bool(for_print),
            mapping_file or None,
        )
        success = Path(out_path).exists()
    except Exception as e:
        report = "[arch-lw error] {}: {}".format(type(e).__name__, e)
        success = False
else:
    report = "Set `run = True` to execute."
