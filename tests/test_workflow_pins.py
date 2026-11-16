"""ALW-44: every GitHub Action is pinned to a full commit id, not a movable tag."""

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
USES = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.M)
PINNED = re.compile(r"[^@]+@[0-9a-f]{40}")


class WorkflowPinTests(unittest.TestCase):
    def test_alw44_actions_are_pinned_to_full_commit_ids(self):
        refs = [
            ref
            for workflow in sorted(WORKFLOWS.glob("*.y*ml"))
            for ref in USES.findall(workflow.read_text(encoding="utf-8"))
        ]
        self.assertTrue(refs)
        mutable = [ref for ref in refs if not ref.startswith("./") and not PINNED.fullmatch(ref)]
        self.assertEqual(mutable, [])


if __name__ == "__main__":
    unittest.main()
