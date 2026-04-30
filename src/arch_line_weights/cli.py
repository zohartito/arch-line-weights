"""arch-lw CLI — inspect and apply line-weight hierarchy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__
from .apply import apply_to_file
from .apply_jsx import apply_via_jsx
from .classify import auto_by_luminance, explain_mapping, from_user_mapping
from .inspect import inspect_file, color_to_rgb255
from .layer_classify import classify_layer
from .poche import apply_poche
from .presets import PRESETS, get_preset, select_preset


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
def inspect(src: Path, pretty: bool):
    """Report the color / stroke-width distribution of a .ai or .pdf file."""
    rep = inspect_file(str(src))
    indent = 2 if pretty else None
    click.echo(json.dumps(rep.to_dict(), indent=indent))


@cli.command()
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o", "--output",
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
):
    """Rewrite the file with per-color stroke widths."""
    if not (auto or mapping_file):
        raise click.UsageError("provide --mapping FILE or --auto (with optional --preset)")
    if auto and mapping_file:
        raise click.UsageError("--auto and --mapping are mutually exclusive")

    rep = inspect_file(str(src))

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

    click.echo(f"# {len(mapping)} colors mapped using {'user file' if mapping_file else f'auto:{preset}'}", err=True)
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
    click.echo(f"applied {result.strokes_processed:,} strokes across {result.rg_seen:,} color changes", err=True)
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
    "-o", "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path. Defaults to '<src> HIERARCHY.<ext>'.",
)
def apply_jsx_cmd(src: Path, output: Path | None):
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
    out = str(output) if output else None
    click.echo(f"opening {src} in Illustrator and running layer-aware JSX...", err=True)
    result = apply_via_jsx(str(src), out)
    click.echo(result["report"])


@cli.command("poche")
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path. Defaults to '<src> POCHE.<ext>' (or '<src-without-HIERARCHY> POCHE.<ext>').",
)
@click.option(
    "--overrides",
    "overrides_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help='JSON of per-layer strategy overrides: {"TEC_FOUNDATION": {"strategy": "bbox"}, ...}',
)
def poche_cmd(src: Path, output: Path | None, overrides_path: Path | None):
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
    out = str(output) if output else None
    over = str(overrides_path) if overrides_path else None
    click.echo(f"applying poche to {src}...", err=True)
    report = apply_poche(str(src), out, overrides_path=over)
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
        click.echo(
            f"  {marker} {short:50}  {fr.strategy:18}  polys={fr.polygon_count:>3}  conf={fr.confidence:.2f}",
            err=True,
        )


@cli.command("explain-layer")
@click.argument("layer_name")
def explain_layer(layer_name: str):
    """Show what tier+weight the semantic classifier would assign to a layer name.

    \b
    Examples:
        arch-lw explain-layer 'axon::Visible::ClippingPlaneIntersections::TEC_TIMBER_BEAMS'
        arch-lw explain-layer 'axon::Visible::Curves::FLOOR_DATUMS'
    """
    a = classify_layer(layer_name)
    click.echo(f"{a.weight_pt} pt — {a.tier} ({a.why})")


if __name__ == "__main__":
    cli()
