#!/usr/bin/env python3
"""Opt-in vision rubric judge — the perceptual rung above the deterministic pass.

The deterministic ``visual_judge.py`` catches the four *measurable* failure axes.
It cannot see the subtler things the corpus prizes: tonal recede of "beyond"
geometry, material-by-hatch reading, whether the cut genuinely "owns the darkest
value" as a gestalt (spec §1.3, §4.2). This module hands a single render PNG plus
the committed rubric (``benchmarks/visual-rubric.md``) to a vision model and asks
for a structured verdict.

It mirrors ``arch_line_weights.llm_topology`` exactly:

  * OFF by default. Gated on ``ARCH_LW_LLM_FALLBACK`` (unset / "0" → immediate
    ``None``, no import of ``anthropic``, no network, no cost).
  * ``ANTHROPIC_API_KEY`` required when the gate is on; missing → ``None``.
  * ``ARCH_LW_LLM_MODEL`` overrides the model (default ``claude-sonnet-5``).
  * Never raises on its public surface; any failure returns ``None``.

Privacy allow-list: only the render PNG (pixels) and the rubric text leave the
machine. No file paths, layer names, or customer metadata are sent.

This is a *judgement rung*, never a geometry path — consistent with the AGENTS.md
determinism boundary: the deterministic scores gate; the model only opines.
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_VISION_MODEL = "claude-sonnet-5"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUBRIC = REPO_ROOT / "benchmarks" / "visual-rubric.md"

_SYSTEM = (
    "You are a rigorous architectural-drawing critic. You judge a single "
    "section/plan render against a fixed rubric of line-weight hierarchy and "
    "poché quality. Judge only what the rubric names. Reply with STRICT JSON."
)

_INSTRUCTION = """Judge the attached drawing render against this rubric.

<rubric>
{rubric}
</rubric>

Return ONLY this JSON object, no prose:
{{
  "verdict": "pass" | "review",
  "reads_at_a_glance": true | false,
  "cut_owns_darkest": true | false,
  "weight_flatness": true | false,
  "failures": ["short rubric-grounded phrase", ...],
  "confidence": 0.0-1.0
}}
"""


def _png_bytes(image_path: Path) -> bytes | None:
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception:
        return None
    # Downscale so the payload stays small and cheap; detail beyond ~1600px
    # does not change a hierarchy/poché gestalt judgement.
    max_side = 1600
    if max(img.size) > max_side:
        scale = max_side / max(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _enabled() -> bool:
    return os.environ.get("ARCH_LW_LLM_FALLBACK") == "1"


def judge_render_llm(
    image_path: str | Path,
    rubric_path: str | Path | None = None,
    model: str | None = None,
) -> dict[str, Any] | None:
    """Return a structured vision verdict, or ``None`` if disabled/unavailable.

    Callers MUST treat ``None`` as "vision rung skipped" and fall back to the
    deterministic verdict. This function never raises.
    """
    if not _enabled():
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except Exception:
        return None

    rubric_file = Path(rubric_path) if rubric_path else DEFAULT_RUBRIC
    try:
        rubric = rubric_file.read_text()
    except Exception:
        return None
    png = _png_bytes(Path(image_path))
    if png is None:
        return None

    model = model or os.environ.get("ARCH_LW_LLM_MODEL") or DEFAULT_VISION_MODEL
    b64 = base64.standard_b64encode(png).decode("ascii")
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=model,
            max_tokens=600,
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/png", "data": b64},
                        },
                        {"type": "text", "text": _INSTRUCTION.format(rubric=rubric)},
                    ],
                }
            ],
        )
    except Exception:
        return None

    text = "".join(block.text for block in msg.content if getattr(block, "type", None) == "text").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") : text.rfind("}") + 1]
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    if not isinstance(parsed, dict) or parsed.get("verdict") not in {"pass", "review"}:
        return None
    parsed["_model"] = model
    return parsed


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Opt-in vision rubric judge (ARCH_LW_LLM_FALLBACK=1 to enable).")
    p.add_argument("--image", required=True, help="Render PNG to judge")
    p.add_argument("--rubric", default=None, help="Rubric markdown (default benchmarks/visual-rubric.md)")
    p.add_argument("--model", default=None, help=f"Model id (default {DEFAULT_VISION_MODEL})")
    args = p.parse_args(argv)

    result = judge_render_llm(args.image, args.rubric, args.model)
    if result is None:
        print(
            json.dumps(
                {
                    "verdict": None,
                    "note": "vision judge disabled or unavailable "
                    "(set ARCH_LW_LLM_FALLBACK=1 and ANTHROPIC_API_KEY, install anthropic)",
                },
                indent=2,
            )
        )
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
