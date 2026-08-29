"""Live, metered eval for the opt-in vision rubric judge.

Self-skips unless BOTH are set (mirrors tests/eval_llm_topology.py):

    ARCH_LW_LLM_FALLBACK=1 ANTHROPIC_API_KEY=sk-... \
        pytest tests/eval_visual_judge_llm.py -m eval -s

It renders the committed synthetic demo, sends ONLY the PNG + the committed
rubric to the vision model, and asserts a well-formed structured verdict. This
makes a real, metered Anthropic call — keep it opt-in.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DEMO_AFTER = REPO_ROOT / "examples" / "demo-section HIERARCHY.pdf"


def test_vision_judge_disabled_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The gate must return None with no network when disabled — always runs."""
    import visual_judge_llm as vjl

    monkeypatch.delenv("ARCH_LW_LLM_FALLBACK", raising=False)
    assert vjl.judge_render_llm(tmp_path / "nonexistent.png") is None


@pytest.mark.eval
def test_vision_judge_live(tmp_path: Path) -> None:
    if os.environ.get("ARCH_LW_LLM_FALLBACK") != "1":
        pytest.skip("set ARCH_LW_LLM_FALLBACK=1 to run the live vision-judge eval")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("set ANTHROPIC_API_KEY to run the live vision-judge eval (metered)")
    pytest.importorskip("anthropic", reason="install arch-line-weights[llm] to run the eval")

    import visual_judge as vj
    import visual_judge_llm as vjl
    from PIL import Image

    gray, _ppp = vj.render_gray(DEMO_AFTER, 110)
    png = tmp_path / "demo.png"
    Image.fromarray(gray).save(png)

    result = vjl.judge_render_llm(png)
    assert result is not None, "vision judge returned None with the gate on"
    assert result["verdict"] in {"pass", "review"}
    assert 0.0 <= float(result["confidence"]) <= 1.0
    assert isinstance(result.get("failures"), list)
