import runpy
from pathlib import Path


def test_apply_arch_hierarchy_loads_without_ghpython_inputs():
    script = (
        Path(__file__).resolve().parents[1]
        / "integrations"
        / "rhino"
        / "apply_arch_hierarchy.py"
    )

    namespace = runpy.run_path(str(script))

    assert namespace["success"] is False
    assert namespace["out_path"] == ""
    assert namespace["report"] == "Set `run = True` to execute."
