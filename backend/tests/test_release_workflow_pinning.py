from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "bolcap-release.yml"

EXPECTED_ACTIONS = {
    "actions/checkout": "34e114876b0b11c390a56381ad16ebd13914f8d5",
    "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
    "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "softprops/action-gh-release": "3bb12739c298aeb8a4eeaf626c5b8d85266b0e65",
}


class ReleaseWorkflowPinningTests(unittest.TestCase):
    def test_all_github_actions_use_expected_commit_shas(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        refs = re.findall(
            r"^\s*-\s+uses:\s*([^\s#]+)", workflow, flags=re.MULTILINE
        )

        self.assertEqual(
            len(refs),
            len(EXPECTED_ACTIONS),
            "Unexpected number of GitHub Actions references",
        )

        actual = {}
        for ref in refs:
            self.assertIn("@", ref, f"Malformed GitHub Action reference: {ref}")
            action, sha = ref.split("@", 1)
            self.assertRegex(
                sha,
                r"^[0-9a-f]{40}$",
                f"GitHub Action {action} is not pinned to a full commit SHA",
            )
            self.assertNotIn(action, actual, f"Duplicate GitHub Action: {action}")
            actual[action] = sha

        self.assertEqual(actual, EXPECTED_ACTIONS)


if __name__ == "__main__":
    unittest.main()
