"""arch-lw CLI — inspect and apply line-weight hierarchy."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from . import __version__
from .apply import apply_to_file
from .apply_jsx import apply_via_jsx
from .apply_saas import apply_to_file as apply_to_file_saas
from .apply_saas import default_output_path as default_output_path_saas
from .bridge_rhino_ai import bridge_rhino_ai
from .classify import auto_by_luminance, explain_mapping, from_user_mapping
from .cleanup import cleanup_file
from .cleanup import default_output_path as default_output_path_cleanup
from .input_format import UnsupportedInputError, raise_if_unsupported
from .inspect import color_to_rgb255, inspect_file
from .layer_classify import (
    Source,
    classify_layer,
    detect_source,
    explain_source_match,
)
from .layout_jsx import layout_via_jsx, parse_artboard_size, parse_length
from .poche import apply_poche
from .presets import PRESETS, select_preset
from .progress import DEFAULT_PROGRESS_FILE, make_reporter

# CLI-facing source choices. Keep AUTO first so it's the default.
_SOURCE_CHOICES = [Source.AUTO.value, Source.RHINO.value, Source.AUTOCAD.value]

# Bridge-strategy CLI vocabulary, mirrored from poche.BridgeStrategy.
# "best" (default since v0.6.7) routes through bridge.infer_bridges_best,
# which picks the highest-yield among 4 strategies (greedy, backtrack,
# DBSCAN, DBSCAN+backtrack). "greedy" preserves v0.4 behaviour (the legacy
# nearest-neighbour bridger) for backwards compatibility.
_BRIDGE_STRATEGY_CHOICES = ["greedy", "best"]
_BRIDGE_STRATEGY_DEFAULT = "best"


def _resolve_source(
    source_arg: str,
    pdf_metadata: dict | None,
    layer_names: list[str] | None,
) -> tuple[Source, float]:
    """Resolve a `--source auto|rhino|autocad` flag to a concrete Source.

    For `auto`, runs `detect_source` and falls back to `Source.RHINO` if
    detection is inconclusive (so existing behavior is preserved).
    """
    if source_arg == Source.AUTO.value:
        detected, conf = detect_source(pdf_metadata, layer_names)
        if detected == Source.AUTO:
            return Source.RHINO, 0.0  # fall back to Rhino baseline
        return detected, conf
    return Source(source_arg), 1.0  # user-forced — full confidence


def _require_nonempty_auto_mapping(
    mapping: dict[tuple[int, int, int], float],
    *,
    src: Path,
    preset: str,
) -> None:
    if mapping:
        return
    raise click.UsageError(
        f"auto:{preset} found 0 RGB stroke colors in {src.name!r}; "
        "no line-weight hierarchy can be inferred. Re-save/export the file "
        "from Illustrator, or provide --mapping with explicit colors."
    )


def _require_supported_input(src: Path, command: str):
    try:
        return raise_if_unsupported(src, command)
    except UnsupportedInputError as exc:
        raise click.ClickException(str(exc)) from exc


def _command_summary(command: str, src: Path) -> str:
    return f"arch-lw {command} {src}"


def _require_rewriteable_inspection(rep, *, src: Path, command: str) -> None:
    input_format = getattr(rep, "input_format", None) or {}
    if getattr(rep, "total_stroked", 0) > 0:
        return
    reason = input_format.get("no_drawing_reason") or ("No rewriteable stroked geometry was found.")
    raise click.UsageError(
        f"{command} found no rewriteable stroke geometry in {src.name!r}. "
        f"{reason} Nothing was written; run `arch-lw inspect` to confirm "
        "that this is a drawing export rather than a reference/report PDF."
    )


def _default_poche_output_path(src: Path) -> Path:
    return src.with_name(f"{src.stem.replace(' HIERARCHY', '')} POCHE{src.suffix}")


@click.group()
@click.version_option(__version__, prog_name="arch-lw")
def cli():
    """Apply architectural line-weight hierarchy to color-coded vector drawings.

    Typical workflow:

    \b
        arch-lw inspect drawing.ai > inspect.json
        arch-lw apply drawing.ai --auto --preset section
        # or with a hand-edited mapping:
        arch-lw apply drawing.ai --mapping mapping.json
    """


@cli.command()
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--pretty/--no-pretty", default=True, help="Pretty-print JSON output.")
@click.option(
    "--source",
    type=click.Choice(_SOURCE_CHOICES),
    default=Source.AUTO.value,
    show_default=True,
    help="Force a layer-name convention. 'auto' detects from PDF metadata + layer-name shape.",
)
def inspect(src: Path, pretty: bool, source: str):
    """Report the color / stroke-width distribution of a .ai or .pdf file."""
    indent = 2 if pretty else None
    try:
        rep = inspect_file(str(src))
    except UnsupportedInputError as exc:
        click.echo(json.dumps({"input_format": exc.diagnostic.to_dict()}, indent=indent))
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(rep.to_dict(), indent=indent))

    # Layer-source detection (Phase E5). Print to stderr so JSON on stdout
    # stays parseable by automation.
    pdf_metadata = getattr(rep, "pdf_metadata", None) or {}
    layer_names = getattr(rep, "layer_names", None) or []
    resolved, conf = _resolve_source(source, pdf_metadata, layer_names)
    if source == Source.AUTO.value:
        click.echo(
            f"# detected layer-name source: {resolved.value} (confidence={conf:.2f})",
            err=True,
        )
    else:
        click.echo(f"# layer-name source: {resolved.value} (forced via --source)", err=True)


@cli.command()
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path. Defaults to '<src> HIERARCHY.<ext>'.",
)
@click.option(
    "--mapping",
    "mapping_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help='JSON file: {"RGB(r,g,b)": weight_pt, ...}',
)
@click.option(
    "--preset",
    type=click.Choice(sorted(PRESETS)),
    default="section",
    show_default=True,
    help="Tier ladder used by --auto.",
)
@click.option(
    "--scale",
    default="1/4",
    show_default=True,
    help="Plot scale for ISO 128 weight selection (1/16, 1/8, 1/4, 1/2). Used with --for-print.",
)
@click.option(
    "--for-print",
    is_flag=True,
    help="Use ISO 128 standards-aligned weights at the chosen --scale (heavier than the default screen weights).",
)
@click.option(
    "--auto",
    is_flag=True,
    help="Auto-bucket colors into the preset's tiers by luminance + frequency.",
)
@click.option(
    "--default-width",
    type=float,
    default=0.25,
    show_default=True,
    help="Width applied to colors not in the mapping.",
)
@click.option(
    "--keep-pieceinfo",
    is_flag=True,
    help="Don't strip the .ai PieceInfo cache (Illustrator will then ignore the changes — usually a bad idea).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Compute and explain the mapping; don't write any file.",
)
@click.option(
    "--source",
    type=click.Choice(_SOURCE_CHOICES),
    default=Source.AUTO.value,
    show_default=True,
    help="Layer-name convention to use for semantic classification. "
    "'auto' detects from PDF metadata + layer-name shape; "
    "'rhino' = Rhino Make2D + ClippingPlane; 'autocad' = AIA NCS / ISO 13567-2.",
)
def apply(
    src: Path,
    output: Path | None,
    mapping_file: Path | None,
    preset: str,
    scale: str,
    for_print: bool,
    auto: bool,
    default_width: float,
    keep_pieceinfo: bool,
    dry_run: bool,
    source: str,
):
    """Rewrite the file with per-color stroke widths."""
    _require_supported_input(src, "apply")
    if not (auto or mapping_file):
        raise click.UsageError("provide --mapping FILE or --auto (with optional --preset)")
    if auto and mapping_file:
        raise click.UsageError("--auto and --mapping are mutually exclusive")

    rep = inspect_file(str(src))
    _require_rewriteable_inspection(rep, src=src, command="apply")

    # Layer-source resolution. Print so users see what convention drove the
    # classifier; lets them re-run with `--source autocad` if detection is wrong.
    pdf_metadata = getattr(rep, "pdf_metadata", None) or {}
    layer_names = getattr(rep, "layer_names", None) or []
    resolved_source, source_conf = _resolve_source(source, pdf_metadata, layer_names)
    if source == Source.AUTO.value:
        click.echo(
            f"# layer-source: {resolved_source.value} (auto-detected, confidence={source_conf:.2f})",
            err=True,
        )
    else:
        click.echo(f"# layer-source: {resolved_source.value} (forced)", err=True)

    if mapping_file:
        raw = json.loads(mapping_file.read_text())
        mapping: dict[tuple[int, int, int], float] = {}
        for ckey, w in raw.items():
            rgb = color_to_rgb255(ckey)
            if rgb is None:
                click.echo(f"warning: skipping unparseable color {ckey!r}", err=True)
                continue
            mapping[rgb] = float(w)
        mapping = from_user_mapping(mapping)
    else:
        tiers = select_preset(preset, scale=scale, for_print=for_print)
        mapping = auto_by_luminance(rep, tiers)
        _require_nonempty_auto_mapping(mapping, src=src, preset=preset)

    click.echo(
        f"# {len(mapping)} colors mapped using {'user file' if mapping_file else f'auto:{preset}'}",
        err=True,
    )
    for line in explain_mapping(mapping, rep):
        click.echo(line, err=True)

    if dry_run:
        click.echo("--dry-run: no file written.", err=True)
        return

    if output is None:
        output = src.with_name(f"{src.stem} HIERARCHY{src.suffix}")

    result = apply_to_file(
        str(src),
        str(output),
        mapping,
        default_width=default_width,
        strip_pieceinfo=not keep_pieceinfo,
    )

    click.echo("", err=True)
    click.echo(
        f"applied {result.strokes_processed:,} strokes across {result.rg_seen:,} color changes", err=True
    )
    for w in sorted(result.weights_applied):
        click.echo(f"  {w:>5} pt  →  {result.weights_applied[w]:>7,} strokes", err=True)
    if result.unmatched_colors:
        click.echo("", err=True)
        click.echo(f"unmatched (defaulted to {default_width} pt):", err=True)
        for rgb, n in sorted(result.unmatched_colors.items(), key=lambda kv: -kv[1])[:10]:
            click.echo(f"  RGB{rgb}: {n}", err=True)
    click.echo("", err=True)
    click.echo(f"wrote {output}  ({result.output_size:,} bytes)", err=True)


@cli.command("apply-jsx")
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path. Defaults to '<src> HIERARCHY-jsx.<ext>' "
    "(distinct from apply-saas to avoid output collisions; Issue #12).",
)
@click.option(
    "--preset",
    type=click.Choice(sorted(PRESETS)),
    default="section",
    show_default=True,
    help="Tier ladder used by the embedded JSX classifier. Matches `apply-saas --preset`. Issue #13.",
)
@click.option(
    "--scale",
    default="1/4",
    show_default=True,
    help="Plot scale for ISO 128 weight selection (1/16, 1/8, 1/4, 1/2). Used with --for-print.",
)
@click.option(
    "--for-print",
    is_flag=True,
    help="Use ISO 128 standards-aligned weights at the chosen --scale "
    "(heavier than the default screen weights).",
)
@click.option(
    "--timeout",
    "timeout_min",
    type=click.IntRange(1, 240),
    default=None,
    help="JSX timeout in minutes (default 30, max 240). Honors the "
    "ARCH_LW_JSX_TIMEOUT_MIN env var when omitted. Issue #11.",
)
@click.option(
    "--source",
    type=click.Choice(_SOURCE_CHOICES),
    default=Source.AUTO.value,
    show_default=True,
    help="Layer-name convention used by the embedded JSX classifier.",
)
@click.option(
    "--bridge-strategy",
    type=click.Choice(_BRIDGE_STRATEGY_CHOICES),
    default=_BRIDGE_STRATEGY_DEFAULT,
    show_default=True,
    help="Bridge selector for the auto_bridge rung. 'best' = run all 4 "
    "strategies (greedy, backtrack, DBSCAN, DBSCAN+backtrack) and pick the "
    "highest-yield (default since v0.6.7). 'greedy' = v0.4 nearest-neighbour "
    "bridger (backwards-compat). Only the apply-jsx command's poché step "
    "(if invoked downstream) consumes this; otherwise it's surfaced for "
    "symmetry with `apply-saas`. Also reads the ARCH_LW_BRIDGE_STRATEGY env var.",
)
def apply_jsx_cmd(
    src: Path,
    output: Path | None,
    preset: str,
    scale: str,
    for_print: bool,
    timeout_min: int | None,
    source: str,
    bridge_strategy: str,
):
    """Layer-preserving apply via Illustrator JSX (slower, but keeps every layer).

    \b
    Use this for .ai files where you want all original layers preserved as
    Illustrator layers (so you can later click any layer's target circle and
    refine the weight). Requires Adobe Illustrator 2024+ installed.

    \b
    The 'apply' command (pikepdf) is faster but flattens the file's layer
    structure into 1 Illustrator layer. 'apply-jsx' is the right default for
    Rhino-exported drawings with meaningful OCG layer names.
    """
    _require_supported_input(src, "apply-jsx")
    out = str(output) if output else None
    if source != Source.AUTO.value:
        click.echo(f"# layer-source: {source} (forced)", err=True)
    if bridge_strategy != _BRIDGE_STRATEGY_DEFAULT:
        click.echo(f"# bridge-strategy: {bridge_strategy} (forced via --bridge-strategy)", err=True)
        # Surface to downstream consumers via env var; the JSX path itself
        # doesn't currently call the polygonize_layer ladder, but if a future
        # poché-via-JSX step does, it'll inherit the selection.
        os.environ["ARCH_LW_BRIDGE_STRATEGY"] = bridge_strategy
    # Section preset is the v0.5.1 default. Preserve byte-identical JSX
    # output by passing `preset=None` (no override), so existing users see
    # zero behaviour change. Issue #13 only takes effect when the user
    # explicitly picks plan / elevation / detail (or asks for --for-print).
    effective_preset: str | None
    if preset == "section" and not for_print:
        effective_preset = None
    else:
        effective_preset = preset
        click.echo(f"# preset: {preset} (forced via --preset)", err=True)
    if for_print:
        click.echo(f"# for-print: scale={scale}", err=True)
    click.echo(f"opening {src} in Illustrator and running layer-aware JSX...", err=True)
    result = apply_via_jsx(
        str(src),
        out,
        timeout_min=timeout_min,
        preset=effective_preset,
        scale=scale,
        for_print=for_print,
        printer=lambda s: click.echo(s, err=True),
    )
    click.echo(result["report"])


@cli.command("layout-jsx")
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path. Defaults to '<src> LAYOUT-jsx.<ext>'.",
)
@click.option(
    "--artboard",
    default="24x36in",
    show_default=True,
    help="Artboard size as WIDTHxHEIGHT. Bare values are inches; 'pt' is also supported.",
)
@click.option(
    "--fit",
    "fit_mode",
    type=click.Choice(["center", "fit"]),
    default="center",
    show_default=True,
    help="'center' keeps scale and recenters; 'fit' scales down to fit within the margin.",
)
@click.option(
    "--margin",
    default="0.5in",
    show_default=True,
    help="Margin used by --fit. Bare values are inches; 'pt' is also supported.",
)
@click.option(
    "--allow-enlarge",
    is_flag=True,
    help="Allow --fit to scale artwork up when it is smaller than the target artboard.",
)
@click.option(
    "--report-json",
    "report_json",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write/read a structured JSON layout report.",
)
@click.option(
    "--jsx-path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path for the generated Illustrator JSX bridge script.",
)
@click.option(
    "--timeout",
    "timeout_min",
    type=click.IntRange(1, 240),
    default=None,
    help="JSX timeout in minutes (default 30, max 240). Honors ARCH_LW_JSX_TIMEOUT_MIN when omitted.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Render the JSX/report contract without opening Illustrator or writing output artwork.",
)
def layout_jsx_cmd(
    src: Path,
    output: Path | None,
    artboard: str,
    fit_mode: str,
    margin: str,
    allow_enlarge: bool,
    report_json: Path | None,
    jsx_path: Path | None,
    timeout_min: int | None,
    dry_run: bool,
):
    """Open a Rhino/Illustrator export, set artboard size, fit/center, and save.

    \b
    This is the narrow bridge for Make2D output after Rhino export and before
    line hierarchy/poché work. It does not classify strokes or change drawing
    content; it makes the Illustrator document inspectable and centered on a
    known sheet size.
    """
    try:
        parse_artboard_size(artboard)
    except ValueError as exc:
        raise click.UsageError(f"invalid artboard: {exc}") from exc
    try:
        parse_length(margin)
    except ValueError as exc:
        raise click.UsageError(f"invalid margin: {exc}") from exc

    try:
        result = layout_via_jsx(
            str(src),
            dst=str(output) if output else None,
            artboard=artboard,
            fit_mode=fit_mode,
            margin=margin,
            allow_enlarge=allow_enlarge,
            report_json=str(report_json) if report_json else None,
            jsx_path=str(jsx_path) if jsx_path else None,
            timeout_min=timeout_min,
            dry_run=dry_run,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    if dry_run:
        click.echo(f"layout: dry run wrote JSX {result['jsx_path']}", err=True)
    else:
        click.echo(f"layout: wrote {result['output']}", err=True)
    click.echo(f"layout: report {result['report_json']}", err=True)
    if result.get("report"):
        click.echo(result["report"])


@cli.command("bridge-rhino-ai")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Rhino Export Selected `.ai` or `.pdf` file.",
)
@click.option(
    "-o",
    "--output",
    "layout_output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Layout output path. Defaults to '<input> LAYOUT-jsx.<ext>'.",
)
@click.option(
    "--artboard",
    default="24x36in",
    show_default=True,
    help="Target artboard size as WIDTHxHEIGHT.",
)
@click.option(
    "--fit",
    "fit_mode",
    type=click.Choice(["center", "fit"]),
    default="center",
    show_default=True,
    help="Keep scale and center, or scale down to fit within the margin.",
)
@click.option("--margin", default="0.5in", show_default=True, help="Margin used by --fit.")
@click.option("--allow-enlarge", is_flag=True, help="Allow --fit to scale artwork up.")
@click.option(
    "--preset",
    type=click.Choice(sorted(PRESETS)),
    default="section",
    show_default=True,
    help="Preset passed to optional --apply-jsx.",
)
@click.option(
    "--source",
    type=click.Choice(_SOURCE_CHOICES),
    default=Source.RHINO.value,
    show_default=True,
    help="Layer-name convention recorded for reports and optional poché.",
)
@click.option("--scale", default="1/4", show_default=True, help="Plot scale for optional --apply-jsx.")
@click.option("--for-print", is_flag=True, help="Use print weights in optional --apply-jsx.")
@click.option("--apply-jsx", "run_apply_jsx", is_flag=True, help="Run hierarchy after layout.")
@click.option("--poche", "run_poche", is_flag=True, help="Run poché after --apply-jsx.")
@click.option(
    "--poche-style",
    type=click.Choice(["solid", "material"]),
    default="solid",
    show_default=True,
    help="Style passed to optional poché.",
)
@click.option(
    "--bridge-strategy",
    type=click.Choice(_BRIDGE_STRATEGY_CHOICES),
    default=_BRIDGE_STRATEGY_DEFAULT,
    show_default=True,
    help="Bridge selector passed to optional poché.",
)
@click.option(
    "--report-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory for bridge/layout/poché reports and generated JSX.",
)
@click.option(
    "--timeout",
    "timeout_min",
    type=click.IntRange(1, 240),
    default=None,
    help="Illustrator JSX timeout in minutes.",
)
@click.option("--dry-run", is_flag=True, help="Plan stages and render layout JSX/report without GUI work.")
def bridge_rhino_ai_cmd(
    input_path: Path,
    layout_output: Path | None,
    artboard: str,
    fit_mode: str,
    margin: str,
    allow_enlarge: bool,
    preset: str,
    source: str,
    scale: str,
    for_print: bool,
    run_apply_jsx: bool,
    run_poche: bool,
    poche_style: str,
    bridge_strategy: str,
    report_dir: Path | None,
    timeout_min: int | None,
    dry_run: bool,
):
    """Run the Rhino Make2D -> Illustrator layout bridge.

    \b
    The first stage always runs `layout-jsx`. Optional stages continue into
    `apply-jsx` and `poche`, but launch-proof decisions still depend on the
    verification reports and visual QA gates.
    """
    if run_poche and not run_apply_jsx:
        raise click.UsageError("--poche requires --apply-jsx")
    try:
        parse_artboard_size(artboard)
        parse_length(margin)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    try:
        result = bridge_rhino_ai(
            str(input_path),
            layout_output=str(layout_output) if layout_output else None,
            artboard=artboard,
            fit_mode=fit_mode,
            margin=margin,
            allow_enlarge=allow_enlarge,
            preset=preset,
            source=source,
            scale=scale,
            for_print=for_print,
            run_apply_jsx=run_apply_jsx,
            run_poche=run_poche,
            report_dir=str(report_dir) if report_dir else None,
            timeout_min=timeout_min,
            bridge_strategy=bridge_strategy,
            poche_style=poche_style,
            dry_run=dry_run,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"bridge: {result['summary']['status']}", err=True)
    click.echo(f"bridge: report {result['report_json']}", err=True)
    for stage in result["stages"]:
        click.echo(f"  {stage['name']}: {stage['status']} -> {stage.get('output', '')}", err=True)
    click.echo(json.dumps(result, indent=2, sort_keys=True))


@cli.command("apply-saas")
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path. Defaults to '<src> HIERARCHY-saas.<ext>' "
    "(distinct from apply-jsx to avoid output collisions; Issue #12).",
)
@click.option(
    "--mapping",
    "mapping_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help='JSON file: {"RGB(r,g,b)": weight_pt, ...}',
)
@click.option(
    "--preset",
    type=click.Choice(sorted(PRESETS)),
    default="section",
    show_default=True,
    help="Tier ladder used by --auto.",
)
@click.option(
    "--scale",
    default="1/4",
    show_default=True,
    help="Plot scale for ISO 128 weight selection (1/16, 1/8, 1/4, 1/2). Used with --for-print.",
)
@click.option(
    "--for-print",
    is_flag=True,
    help="Use ISO 128 standards-aligned weights at the chosen --scale.",
)
@click.option(
    "--auto",
    is_flag=True,
    help="Auto-bucket colors into the preset's tiers by luminance + frequency.",
)
@click.option(
    "--architectural",
    is_flag=True,
    help="Use semantic architectural layer rules before color luminance. "
    "Keeps structural cut mass heavy while connectors, glass, cladding, "
    "membranes, and entourage stay subordinate.",
)
@click.option(
    "--default-width",
    type=float,
    default=0.25,
    show_default=True,
    help="Width applied to colors not in the mapping.",
)
@click.option(
    "--poche",
    is_flag=True,
    help="Also inject solid-black poché fills into ClippingPlaneIntersections layers "
    "(headless, no Illustrator install needed).",
)
@click.option(
    "--poche-overrides",
    "poche_overrides_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON of per-layer poché strategy overrides; same schema as `arch-lw poche --overrides`.",
)
@click.option(
    "--poche-overlay/--inline-poche",
    "poche_overlay",
    default=None,
    help="Write generated poché to a top ARCH_LW_POCHE layer instead of injecting "
    "fills into source cut layers. Defaults ON for --architectural --poche, "
    "otherwise follows ARCH_LW_POCHE_OVERLAY.",
)
@click.option(
    "--alpha-shape/--no-alpha-shape",
    default=True,
    show_default=True,
    help="Enable the α-shape rescue rung between auto_bridge and concave_hull. "
    "v0.5.2 default ON: improves fidelity for layers with multi-component "
    "topology (e.g. 26_CLT_GAP_ROOF_CAP). Pass --no-alpha-shape to revert "
    "to the v0.5.1 ladder.",
)
@click.option(
    "--bridge-strategy",
    type=click.Choice(_BRIDGE_STRATEGY_CHOICES),
    default=_BRIDGE_STRATEGY_DEFAULT,
    show_default=True,
    help="Bridge selector for the auto_bridge rung when --poche is set. "
    "'best' = run all 4 strategies (greedy, backtrack, DBSCAN, "
    "DBSCAN+backtrack) and pick the highest-yield (default since v0.6.7). "
    "'greedy' = v0.4 nearest-neighbour bridger (backwards-compat). "
    "Also reads the ARCH_LW_BRIDGE_STRATEGY env var.",
)
@click.option(
    "--llm-fallback",
    is_flag=True,
    default=False,
    help="Enable the LLM topology-inference rescue rung (rung 5, between "
    "alpha_shape and concave_hull). Opt-in only — sends layer names + "
    "endpoint coordinates (no filenames, no metadata) to Anthropic Claude "
    "Haiku for a closure plan when all geometric rungs fail. Requires the "
    "anthropic package (install the `llm` extra from a source checkout, e.g. "
    "`.venv/bin/python -m pip install -e '.[llm]'`) "
    "and ANTHROPIC_API_KEY in the environment. ~$0.003/stubborn layer. "
    "See docs/research/ai-augmented-mode.md.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Compute and explain the mapping; don't write any file.",
)
@click.option(
    "--source",
    type=click.Choice(_SOURCE_CHOICES),
    default=Source.AUTO.value,
    show_default=True,
    help="Layer-name convention. 'auto' detects from PDF metadata + layer-name shape; "
    "'rhino' = Rhino Make2D; 'autocad' = AIA NCS.",
)
@click.option(
    "--progress/--no-progress",
    "progress",
    default=None,
    help="Per-stage / per-layer progress feedback (Issue #15). Default: ON when "
    "stderr is a TTY, OFF when piped. --no-progress is fully no-op (no stderr "
    "output, no file write). Events also written to --progress-file for "
    "external tailers.",
)
@click.option(
    "--progress-file",
    "progress_file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=f"Override the progress-event log path (default: {DEFAULT_PROGRESS_FILE}). "
    "One tab-separated event per line. Ignored when --no-progress is set.",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write a durable JSON run report with filled/inferred/skipped/review layers.",
)
def apply_saas_cmd(
    src: Path,
    output: Path | None,
    mapping_file: Path | None,
    preset: str,
    scale: str,
    for_print: bool,
    auto: bool,
    architectural: bool,
    default_width: float,
    poche: bool,
    poche_overrides_path: Path | None,
    poche_overlay: bool | None,
    alpha_shape: bool,
    bridge_strategy: str,
    llm_fallback: bool,
    dry_run: bool,
    source: str,
    progress: bool | None,
    progress_file: Path | None,
    report_path: Path | None,
):
    """Headless apply: modify the AI native payload directly (preserves layers).

    \b
    Like `apply` but operates on Illustrator's authoritative
    `/PieceInfo /Illustrator /Private` payload rather than the PDF content
    stream. The OCG layer hierarchy (and PieceInfo cache) is preserved, so
    the result opens in Illustrator with every original layer intact and
    no Illustrator install is required server-side.

    \b
    Best for SaaS / batch workflows on Rhino-exported `.ai` files. For
    plain `.pdf` files (no PieceInfo), use `apply` instead.
    """
    input_diag = _require_supported_input(src, "apply-saas")
    if not (auto or mapping_file or architectural):
        raise click.UsageError("provide --mapping FILE, --auto (with optional --preset), or --architectural")
    if auto and mapping_file:
        raise click.UsageError("--auto and --mapping are mutually exclusive")

    rep = inspect_file(str(src))
    _require_rewriteable_inspection(rep, src=src, command="apply-saas")

    pdf_metadata = getattr(rep, "pdf_metadata", None) or {}
    layer_names = getattr(rep, "layer_names", None) or []
    resolved_source, source_conf = _resolve_source(source, pdf_metadata, layer_names)
    if source == Source.AUTO.value:
        click.echo(
            f"# layer-source: {resolved_source.value} (auto-detected, confidence={source_conf:.2f})",
            err=True,
        )
    else:
        click.echo(f"# layer-source: {resolved_source.value} (forced)", err=True)

    if mapping_file:
        raw = json.loads(mapping_file.read_text())
        mapping: dict[tuple[int, int, int], float] = {}
        for ckey, w in raw.items():
            rgb = color_to_rgb255(ckey)
            if rgb is None:
                click.echo(f"warning: skipping unparseable color {ckey!r}", err=True)
                continue
            mapping[rgb] = float(w)
        mapping = from_user_mapping(mapping)
    elif auto:
        tiers = select_preset(preset, scale=scale, for_print=for_print)
        mapping = auto_by_luminance(rep, tiers)
        if not architectural:
            _require_nonempty_auto_mapping(mapping, src=src, preset=preset)
    else:
        mapping = {}

    mapping_label = "user file" if mapping_file else (f"auto:{preset}" if auto else "architectural")
    click.echo(f"# {len(mapping)} colors mapped using {mapping_label}", err=True)
    for line in explain_mapping(mapping, rep):
        click.echo(line, err=True)
    if architectural:
        click.echo("# architectural: semantic layer rules enabled", err=True)

    layer_weight_resolver = None
    layer_color_resolver = None
    layer_solid_line_resolver = None
    if architectural:
        from .architectural import (
            architectural_layer_color_resolver,
            architectural_layer_solid_line_resolver,
            architectural_layer_weight_resolver,
        )

        layer_weight_resolver = architectural_layer_weight_resolver(
            preset=preset,
            scale=scale,
            for_print=for_print,
            source=resolved_source,
        )
        layer_color_resolver = architectural_layer_color_resolver(
            preset=preset,
            scale=scale,
            for_print=for_print,
            source=resolved_source,
        )
        layer_solid_line_resolver = architectural_layer_solid_line_resolver(
            preset=preset,
            scale=scale,
            for_print=for_print,
            source=resolved_source,
        )

    if dry_run:
        click.echo("--dry-run: no file written.", err=True)
        return

    # Issue #12: distinct default output path from apply-jsx so concurrent
    # runs of both pipelines on the same source don't race / overwrite.
    if output is None:
        output = Path(default_output_path_saas(src))

    # Resolve the --progress flag. Default ON when stderr is a TTY, OFF when
    # piped (so wrapped invocations don't pollute stdout/stderr captures).
    if progress is None:
        progress_enabled = sys.stderr.isatty() if hasattr(sys.stderr, "isatty") else False
    else:
        progress_enabled = bool(progress)
    progress_file_path = str(progress_file) if progress_file else DEFAULT_PROGRESS_FILE
    reporter = make_reporter(
        enabled=progress_enabled,
        file_path=progress_file_path if progress_enabled else None,
        stderr=sys.stderr if progress_enabled else None,
    )

    if poche:
        from .poche_saas import apply_saas_with_poche

        overrides = {}
        if poche_overrides_path:
            overrides = json.loads(poche_overrides_path.read_text())
        resolved_poche_overlay = True if architectural and poche_overlay is None else poche_overlay

        # Surface --llm-fallback to the polygonize ladder via the env var
        # gate. The flag's lifetime is the duration of the CLI run; we
        # don't unset on exit because the process is exiting anyway.
        if llm_fallback:
            os.environ["ARCH_LW_LLM_FALLBACK"] = "1"
            click.echo("# llm-fallback: enabled (rung 5)", err=True)

        try:
            result, poche_result, poche_report = apply_saas_with_poche(
                str(src),
                str(output),
                mapping,
                default_width=default_width,
                overrides=overrides,
                use_alpha_shape=alpha_shape,
                bridge_strategy=bridge_strategy,
                reporter=reporter,
                layer_weight_resolver=layer_weight_resolver,
                layer_color_resolver=layer_color_resolver,
                layer_solid_line_resolver=layer_solid_line_resolver,
                poche_overlay=resolved_poche_overlay,
                architectural=architectural,
                preset=preset,
                scale=scale,
                for_print=for_print,
                source=resolved_source,
            )
        finally:
            reporter.close()
    else:
        if poche_overrides_path:
            click.echo(
                "warning: --poche-overrides has no effect without --poche",
                err=True,
            )
        if poche_overlay is not None:
            click.echo(
                "warning: --poche-overlay/--inline-poche has no effect without --poche",
                err=True,
            )
        if not alpha_shape:
            click.echo(
                "warning: --no-alpha-shape has no effect without --poche",
                err=True,
            )
        if bridge_strategy != _BRIDGE_STRATEGY_DEFAULT:
            click.echo(
                "warning: --bridge-strategy has no effect without --poche",
                err=True,
            )
        if llm_fallback:
            click.echo(
                "warning: --llm-fallback has no effect without --poche",
                err=True,
            )
        try:
            result = apply_to_file_saas(
                str(src),
                str(output),
                mapping,
                default_width=default_width,
                reporter=reporter,
                layer_weight_resolver=layer_weight_resolver,
                layer_color_resolver=layer_color_resolver,
                layer_solid_line_resolver=layer_solid_line_resolver,
            )
        finally:
            reporter.close()
        poche_result = None
        poche_report = None

    click.echo("", err=True)
    click.echo(
        f"rewrote {result.widths_rewritten:,} stroke-width ops across {result.xa_seen:,} stroke-color sets",
        err=True,
    )
    click.echo(
        f"payload: {result.payload_size_in:,} → {result.payload_size_out:,} bytes "
        f"({result.chunks_in} → {result.chunks_out} chunks)",
        err=True,
    )
    for w in sorted(result.weights_applied):
        click.echo(f"  {w:>5} pt  →  {result.weights_applied[w]:>7,} ops", err=True)
    if result.layer_weight_overrides:
        click.echo(
            f"  architectural layer overrides → {result.layer_weight_overrides:>7,} ops",
            err=True,
        )
    if result.layer_color_overrides:
        click.echo(
            f"  architectural color overrides → {result.layer_color_overrides:>7,} ops",
            err=True,
        )
    if result.layer_dash_overrides:
        click.echo(
            f"  architectural dash overrides → {result.layer_dash_overrides:>7,} ops",
            err=True,
        )
    if result.unmatched_colors:
        click.echo("", err=True)
        click.echo(f"unmatched (defaulted to {default_width} pt):", err=True)
        for rgb, n in sorted(result.unmatched_colors.items(), key=lambda kv: -kv[1])[:10]:
            click.echo(f"  RGB{rgb}: {n}", err=True)

    if poche_result is not None and poche_report is not None:
        click.echo("", err=True)
        click.echo(
            f"poché: injected {poche_result.polygons_injected} polygons across "
            f"{poche_result.layers_injected}/{poche_result.layers_targeted} cut layers "
            f"(+{poche_result.bytes_injected:,} bytes)",
            err=True,
        )
        if poche_result.layers_missing:
            click.echo(
                f"  warning: {len(poche_result.layers_missing)} layer(s) had polygons "
                "but couldn't be located in the payload:",
                err=True,
            )
            for n in poche_result.layers_missing[:10]:
                click.echo(f"    {n}", err=True)
        for fr in sorted(poche_report.fills, key=lambda f: -f.confidence):
            short = fr.layer.split("::")[-1]
            marker = "✓" if fr.confidence >= 0.85 else ("~" if fr.confidence > 0 else "✗")
            click.echo(
                f"  {marker} {short:50}  {fr.strategy:18}  polys={fr.polygon_count:>3}  "
                f"conf={fr.confidence:.2f}",
                err=True,
            )
    if report_path is not None:
        from .run_report import build_apply_saas_report

        run_report = build_apply_saas_report(
            input_path=src,
            output_path=output,
            source={
                "mode": "apply-saas",
                "architectural": architectural,
                "preset": preset,
                "scale": scale,
                "layer_source": resolved_source.value,
                "poche_overlay": bool(resolved_poche_overlay) if poche else False,
                "bridge_strategy": bridge_strategy,
                "min_inject_confidence": 0.85,
            },
            poche_report=poche_report,
            poche_result=poche_result,
            input_format=input_diag.to_dict(),
            command=_command_summary("apply-saas", src),
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(run_report, indent=2, sort_keys=True) + "\n")
        click.echo(f"report: wrote {report_path}", err=True)

    click.echo("", err=True)
    click.echo(f"wrote {output}  ({result.output_size:,} bytes)", err=True)


@cli.command("cleanup")
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path. Defaults to '<src> CLEANUP.<ext>'.",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write a JSON cleanup report with deleted/lightened/medium/heavy counts.",
)
def cleanup_cmd(src: Path, output: Path | None, report_path: Path | None):
    """Conservatively clean up a low-semantic one-layer AI drawing."""
    if output is None:
        output = Path(default_output_path_cleanup(src))

    try:
        result = cleanup_file(str(src), str(output))
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    report = result.report.to_dict()
    report["source"] = {
        "mode": "cleanup",
        "input": src.name,
        "output": output.name,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        click.echo(f"report: wrote {report_path}", err=True)

    summary = report["summary"]
    click.echo(
        "cleanup: "
        f"deleted={summary['deleted']} "
        f"lightened={summary['lightened']} "
        f"medium={summary['medium']} "
        f"heavy={summary['heavy']}",
        err=True,
    )
    for warning in report["warnings"]:
        click.echo(f"warning: {warning}", err=True)
    click.echo(f"wrote {output}  ({result.output_size:,} bytes)", err=True)


@cli.command("poche")
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path. Defaults to '<src> POCHE.<ext>' (or '<src-without-HIERARCHY> POCHE.<ext>').",
)
@click.option(
    "--overrides",
    "overrides_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help='JSON of per-layer strategy overrides: {"TEC_FOUNDATION": {"strategy": "bbox"}, ...}',
)
@click.option(
    "--style",
    type=click.Choice(["solid", "material"]),
    default="solid",
    show_default=True,
    help="solid = black fill only; material = fill + per-material hatch (concrete diagonal, CLT cross-grain, etc.)",
)
@click.option(
    "--scale",
    "hatch_scale",
    type=float,
    default=0.02,
    show_default=True,
    help="Plot scale (1/N as decimal). 0.02 = 1:50, 0.01 = 1:100. Used only when --style material.",
)
@click.option(
    "--alpha-shape/--no-alpha-shape",
    default=True,
    show_default=True,
    help="Enable the α-shape rescue rung between auto_bridge and concave_hull. "
    "v0.5.2 default ON: improves fidelity for layers with multi-component "
    "topology (e.g. 26_CLT_GAP_ROOF_CAP). Pass --no-alpha-shape to revert "
    "to the v0.5.1 ladder.",
)
@click.option(
    "--bridge-strategy",
    type=click.Choice(_BRIDGE_STRATEGY_CHOICES),
    default=_BRIDGE_STRATEGY_DEFAULT,
    show_default=True,
    help="Bridge selector for the auto_bridge rung. 'best' = run all 4 "
    "strategies (greedy, backtrack, DBSCAN, DBSCAN+backtrack) and pick "
    "the highest-yield (default since v0.6.7; benefits the 3 stubborn cut "
    "layers from the v0.5 review). 'greedy' = v0.4 nearest-neighbour "
    "bridger (backwards-compat with v0.5.x). Also reads "
    "ARCH_LW_BRIDGE_STRATEGY env var.",
)
@click.option(
    "--llm-fallback",
    is_flag=True,
    default=False,
    help="Enable the LLM topology-inference rescue rung (rung 5, between "
    "alpha_shape and concave_hull). Opt-in only — sends layer names + "
    "endpoint coordinates (no filenames, no metadata) to Anthropic Claude "
    "Haiku for a closure plan when all geometric rungs fail. Requires the "
    "anthropic package (install the `llm` extra from a source checkout, e.g. "
    "`.venv/bin/python -m pip install -e '.[llm]'`) "
    "and ANTHROPIC_API_KEY in the environment. ~$0.003/stubborn layer. "
    "See docs/research/ai-augmented-mode.md.",
)
@click.option(
    "--source",
    type=click.Choice(_SOURCE_CHOICES),
    default=Source.AUTO.value,
    show_default=True,
    help="Layer-name convention used to identify cut layers (only Rhino "
    "ClippingPlaneIntersections is currently a poché target; AIA NCS support is preliminary).",
)
@click.option(
    "--report-json",
    "report_json",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write a structured JSON poché report for verification gates.",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Alias for --report-json; writes a durable JSON run report with filled/skipped/failed/why layer status.",
)
@click.option(
    "--geometry-json",
    "geometry_json",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write a redacted cut-geometry summary JSON for verification gates.",
)
def poche_cmd(
    src: Path,
    output: Path | None,
    overrides_path: Path | None,
    style: str,
    hatch_scale: float,
    alpha_shape: bool,
    bridge_strategy: str,
    llm_fallback: bool,
    source: str,
    report_json: Path | None,
    report_path: Path | None,
    geometry_json: Path | None,
):
    """Generate solid-black poché on cut layers via shapely linemerge + polygonize.

    \b
    The two-stage pipeline opens the file in Adobe Illustrator, dumps every
    `Visible::ClippingPlaneIntersections::*` layer's path geometry to JSON,
    runs shapely.ops.linemerge + polygonize per layer (with snap-tolerance
    sweep + concave_hull/bbox fallback), then a second JSX writes new closed
    pathItems with black fill into each cut layer and saves the result.

    \b
    Layers preserved. Original strokes preserved. New filled polygons sit
    on top of the existing strokes for the classic "cut reads black" look.

    \b
    Per-layer override JSON example:
      {
        "axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION": {
          "strategy": "bbox"
        },
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE": {
          "strategy": "concave_hull", "ratio": 0.4
        }
      }
    """
    input_diag = _require_supported_input(src, "poche")
    resolved_output = output if output else _default_poche_output_path(src)
    resolved_report_json = report_path or report_json
    out = str(resolved_output)
    over = str(overrides_path) if overrides_path else None
    if source != Source.AUTO.value:
        click.echo(f"# layer-source: {source} (forced)", err=True)
    if bridge_strategy != _BRIDGE_STRATEGY_DEFAULT:
        click.echo(f"# bridge-strategy: {bridge_strategy} (forced via --bridge-strategy)", err=True)
    if llm_fallback:
        os.environ["ARCH_LW_LLM_FALLBACK"] = "1"
        click.echo("# llm-fallback: enabled (rung 5)", err=True)
    click.echo(f"applying poche to {src} (style={style}, scale=1:{int(1 / hatch_scale)})...", err=True)
    try:
        report = apply_poche(
            str(src),
            out,
            overrides_path=over,
            style=style,
            scale=hatch_scale,
            use_alpha_shape=alpha_shape,
            bridge_strategy=bridge_strategy,
            geometry_report_path=str(geometry_json) if geometry_json else None,
        )
    except Exception as exc:
        if resolved_report_json is not None:
            from .run_report import build_poche_report

            run_report = build_poche_report(
                input_path=src,
                output_path=resolved_output,
                source={
                    "mode": "poche",
                    "style": style,
                    "scale": hatch_scale,
                    "layer_source": source,
                    "bridge_strategy": bridge_strategy,
                    "min_inject_confidence": 0.85,
                },
                poche_report=None,
                error=str(exc),
            )
            resolved_report_json.parent.mkdir(parents=True, exist_ok=True)
            resolved_report_json.write_text(json.dumps(run_report, indent=2, sort_keys=True) + "\n")
            click.echo(f"report: wrote {resolved_report_json}", err=True)
        raise
    click.echo("", err=True)
    click.echo(f"polygons created: {report.total_polygons}", err=True)
    click.echo(f"  clean (linemerge):     {report.working_layers} layers", err=True)
    click.echo(f"  imperfect (concave):   {report.imperfect_layers} layers", err=True)
    click.echo(f"  failed:                {report.failed_layers} layers", err=True)
    click.echo("", err=True)
    click.echo("per-layer:", err=True)
    for fr in sorted(report.fills, key=lambda f: -f.confidence):
        short = fr.layer.split("::")[-1]
        marker = "✓" if fr.confidence >= 0.85 else ("~" if fr.confidence > 0 else "✗")
        # Surface bridge_strategy_name when set (only the auto_bridge rung
        # populates it, and only when bridge_strategy="best" was selected).
        bridge_suffix = f"  bridge={fr.bridge_strategy_name}" if fr.bridge_strategy_name else ""
        click.echo(
            f"  {marker} {short:50}  {fr.strategy:18}  polys={fr.polygon_count:>3}  "
            f"conf={fr.confidence:.2f}{bridge_suffix}",
            err=True,
        )
    if resolved_report_json is not None:
        from .run_report import build_poche_report

        run_report = build_poche_report(
            input_path=src,
            output_path=resolved_output,
            source={
                "mode": "poche",
                "style": style,
                "scale": hatch_scale,
                "layer_source": source,
                "bridge_strategy": bridge_strategy,
                "min_inject_confidence": 0.85,
            },
            poche_report=report,
            input_format=input_diag.to_dict(),
            command=_command_summary("poche", src),
        )
        resolved_report_json.parent.mkdir(parents=True, exist_ok=True)
        resolved_report_json.write_text(json.dumps(run_report, indent=2, sort_keys=True) + "\n")
        click.echo(f"report: wrote {resolved_report_json}", err=True)


@cli.command("preview")
@click.argument("before", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("after", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output PNG path.",
)
@click.option(
    "--mode",
    type=click.Choice(["side-by-side", "tier-overlay", "diff"]),
    default="side-by-side",
    show_default=True,
)
@click.option(
    "--dpi",
    type=int,
    default=96,
    show_default=True,
    help="Render DPI (effective resolution; supersample 4× then downsample).",
)
@click.option(
    "--ghostscript",
    is_flag=True,
    help="Use Ghostscript fallback (-dNOMINLINEWIDTH) for sub-0.25pt hairline accuracy.",
)
def preview_cmd(before: Path, after: Path, output: Path, mode: str, dpi: int, ghostscript: bool):
    """Generate a visual before/after preview PNG.

    \b
    Modes:
      side-by-side  — both files rendered at multiple plot scales, stacked
      tier-overlay  — `after` rendered with each tier in a unique color
      diff          — pixel diff (red = added strokes, blue = removed)
    """
    from .preview import GhostscriptRenderer, diff_image, side_by_side, tier_overlay

    renderer = GhostscriptRenderer() if ghostscript else None
    if mode == "side-by-side":
        click.echo("rendering before+after at multiple scales...", err=True)
        side_by_side(str(before), str(after), str(output), renderer=renderer)
    elif mode == "tier-overlay":
        click.echo(f"rendering tier overlay of {after}...", err=True)
        tier_colors = {1.0: "red", 0.5: "orange", 0.3: "yellow", 0.18: "green", 0.13: "cyan", 0.08: "blue"}
        tier_overlay(str(after), str(output), tier_colors, dpi=dpi, renderer=renderer)
    elif mode == "diff":
        click.echo("rendering pixel diff...", err=True)
        diff_image(str(before), str(after), str(output), dpi=dpi, renderer=renderer)
    click.echo(f"wrote {output}", err=True)


@cli.command("explain-layer")
@click.argument("layer_name")
@click.option(
    "--source",
    type=click.Choice(_SOURCE_CHOICES),
    default=Source.AUTO.value,
    show_default=True,
    help="Pattern library to consult. 'auto' infers from the layer name's shape "
    "(e.g. `::`-joined → rhino, `A-WALL-FULL` → autocad).",
)
def explain_layer(layer_name: str, source: str):
    """Show what tier+weight the semantic classifier would assign to a layer name.

    \b
    Examples:
        arch-lw explain-layer 'axon::Visible::ClippingPlaneIntersections::TEC_TIMBER_BEAMS'
        arch-lw explain-layer 'axon::Visible::Curves::FLOOR_DATUMS'
        arch-lw explain-layer 'A-WALL-FULL' --source autocad
    """
    if source == Source.AUTO.value:
        # Single-name detection: use layer-shape inference only (no metadata).
        detected, conf = detect_source(None, [layer_name])
        if detected == Source.AUTO:
            detected = Source.RHINO
            conf = 0.0
        click.echo(
            f"# detected source: {detected.value} (confidence={conf:.2f})",
            err=True,
        )
        click.echo(explain_source_match(layer_name, detected))
    else:
        forced = Source(source)
        click.echo(f"# source: {forced.value} (forced via --source)", err=True)
        click.echo(explain_source_match(layer_name, forced))


# Re-export so the unused `classify_layer` import stays referenced and
# downstream callers can still `from arch_line_weights.cli import classify_layer`.
__all__ = ["classify_layer", "cli"]


if __name__ == "__main__":
    cli()
