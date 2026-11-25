"""Forced polygonization strategies must not fall through to rescue rungs."""

import pytest

from arch_line_weights.poche import polygonize_layer

OPEN = [[[0, 0], [100, 0]], [[100, 0], [100, 100]], [[100, 100], [0, 100]]]
CLOSED = [*OPEN, [[0, 100], [0, 0]]]


@pytest.mark.parametrize("strategy", ["linemerge", "snap"])
def test_alw20_forced_strategy_does_not_fall_through(strategy):
    polys, result = polygonize_layer("TEC_WALL", OPEN, override={"strategy": strategy})
    assert not polys
    assert result.strategy == "failed"
    polys, result = polygonize_layer("TEC_WALL", CLOSED, override={"strategy": strategy})
    assert len(polys) == 1
    assert result.strategy in {"linemerge_bare", "linemerge_snap"}


def test_alw20_rejects_unknown_strategy():
    with pytest.raises(ValueError, match=r"unsupported.*strategy"):
        polygonize_layer("TEC_WALL", OPEN, override={"strategy": "no_such_strategy"})
