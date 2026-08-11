from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from arch_line_weights.hatch import parallel_hatch
from arch_line_weights.proof import build_proof_packet_plan
from arch_line_weights.safety import ProcessingDisabledError


def test_proof_packet_fixture_id_cannot_escape_output_root(tmp_path) -> None:
    with pytest.raises(ValueError, match="safe path component"):
        build_proof_packet_plan(fixture_id="../outside", output_dir=tmp_path, commands=["proof-check"])


def test_material_hatch_rejects_tiny_spacing_before_generating_scanlines() -> None:
    with pytest.raises(ValueError, match="safe limit"):
        parallel_hatch(Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]), 0.0001, 45.0)


def test_freeze_env_blocks_apply_before_open(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ARCH_LW_FREEZE_LEGACY_APPLY", "1")
    with pytest.raises(ProcessingDisabledError, match="disabled"):
        parallel_hatch(Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]), 1.0, 45.0)
