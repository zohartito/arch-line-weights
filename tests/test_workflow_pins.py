"""ALW-44: every GitHub Action is pinned to a full commit id, not a movable tag."""

import re
import unittest
from pathlib import Path

import yaml

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

    def test_alw44_docs_build_has_read_only_permissions(self):
        workflow = yaml.safe_load((WORKFLOWS / "docs.yml").read_text(encoding="utf-8"))
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        build = workflow["jobs"]["build"]
        self.assertEqual(build["permissions"], {"contents": "read"})
        checkout = next(
            step for step in build["steps"] if step.get("uses", "").startswith("actions/checkout@")
        )
        self.assertIs(checkout["with"]["persist-credentials"], False)
        commands = "\n".join(step.get("run", "") for step in build["steps"])
        self.assertIn("uv sync --locked --extra docs", commands)
        self.assertIn("uv run --locked --no-sync mkdocs build", commands)

    def test_alw44_docs_deploy_only_publishes_built_artifact(self):
        workflow = yaml.safe_load((WORKFLOWS / "docs.yml").read_text(encoding="utf-8"))
        deploy = workflow["jobs"]["deploy"]
        self.assertEqual(deploy.get("needs"), "build")
        self.assertEqual(deploy["permissions"], {"contents": "write"})
        # The privileged job must not check out source, install dependencies, or run scripts.
        self.assertTrue(all("run" not in step for step in deploy["steps"]))
        self.assertEqual(
            [step["uses"].split("@")[0] for step in deploy["steps"]],
            ["actions/download-artifact", "peaceiris/actions-gh-pages"],
        )
        download, publish = (step["with"] for step in deploy["steps"])
        upload = next(
            step["with"]
            for step in workflow["jobs"]["build"]["steps"]
            if step.get("uses", "").startswith("actions/upload-artifact@")
        )
        self.assertEqual(download["name"], upload["name"])
        self.assertEqual(download["path"], publish["publish_dir"])
        self.assertEqual(publish["publish_branch"], "gh-pages")
        self.assertEqual(publish["github_token"], "${{ github.token }}")
        self.assertNotIn("external_repository", publish)

    def test_alw44_docs_artifact_preserves_nojekyll(self):
        workflow = yaml.safe_load((WORKFLOWS / "docs.yml").read_text(encoding="utf-8"))
        build = workflow["jobs"]["build"]
        upload_index, upload = next(
            (index, step["with"])
            for index, step in enumerate(build["steps"])
            if step.get("uses", "").startswith("actions/upload-artifact@")
        )
        commands = "\n".join(step.get("run", "") for step in build["steps"][:upload_index])
        self.assertIn(f"touch {upload['path']}/.nojekyll", commands)
        self.assertIs(upload["include-hidden-files"], True)
        self.assertEqual(upload["if-no-files-found"], "error")
        publish = workflow["jobs"]["deploy"]["steps"][-1]["with"]
        self.assertIs(publish["enable_jekyll"], False)


if __name__ == "__main__":
    unittest.main()
