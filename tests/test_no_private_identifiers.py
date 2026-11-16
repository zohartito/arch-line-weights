"""ALW-N5: tracked files must not name the author's workstation or Windows account.

Only SHA-256 fingerprints are stored, so neither this test nor its failure output discloses the names.
"""
import hashlib
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACHINE_FP = "49e7bdf0d9a6603491bdffc40adcc8f94eea9630428db0981599fdb1b7a79ba1"  # two tokens joined by "-"
ACCOUNT_FP = "930705203a1bb60e6de569401ceaa610830d5705fc96ed3c41e7ec5aef4bdd33"  # one token


def _fingerprint(token: bytes) -> str:
    return hashlib.sha256(token).hexdigest()


class PrivateIdentifierTests(unittest.TestCase):
    def test_alwn5_tracked_files_hold_no_private_identifiers(self):
        listed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
        leaked = []
        for name in filter(None, listed.decode("utf-8", "surrogateescape").split("\0")):
            path = ROOT / name
            if not path.is_file():
                continue
            tokens = re.findall(rb"[a-z0-9]+", path.read_bytes().lower())
            pairs = (first + b"-" + second for first, second in zip(tokens, tokens[1:]))
            if any(_fingerprint(token) == ACCOUNT_FP for token in tokens) or any(
                _fingerprint(pair) == MACHINE_FP for pair in pairs
            ):
                leaked.append(name)
        self.assertEqual(leaked, [], "private workstation or account identifier in tracked files")


if __name__ == "__main__":
    unittest.main()
