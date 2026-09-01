"""Mirror test for `hydra_engine.installation.private_tier`."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.installation.private_tier import (  # noqa: E402
    GITIGNORE_BLOCK_HEADER,
    GITIGNORE_RULE,
    PRIVATE_TIER_SEED,
    ensure_gitignore_rule,
    ensure_private_tier,
    private_tier_ignored,
)


def _root() -> Path:
    return Path(tempfile.mkdtemp(prefix="private-tier-"))


def _git_root() -> Path:
    root = _root()
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    return root


def _local(root: Path) -> Path:
    return root / GITIGNORE_RULE.rstrip("/")


class EnsureGitignoreRuleTests(unittest.TestCase):
    def test_adds_rule_when_missing(self) -> None:
        root = _root()
        status = ensure_gitignore_rule(root)
        self.assertEqual(status, "added")
        text = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(GITIGNORE_BLOCK_HEADER, text)
        self.assertIn(GITIGNORE_RULE, text)

    def test_existing_rule_is_not_duplicated(self) -> None:
        root = _root()
        (root / ".gitignore").write_text(f"{GITIGNORE_RULE}\n", encoding="utf-8")
        self.assertEqual(ensure_gitignore_rule(root), "already-present")
        self.assertEqual((root / ".gitignore").read_text(encoding="utf-8").count(GITIGNORE_RULE), 1)

    def test_commented_near_miss_does_not_count(self) -> None:
        root = _root()
        (root / ".gitignore").write_text(f"# {GITIGNORE_RULE}\n", encoding="utf-8")
        self.assertEqual(ensure_gitignore_rule(root), "added")
        self.assertEqual((root / ".gitignore").read_text(encoding="utf-8").count(GITIGNORE_RULE), 2)

    def test_repeat_call_is_idempotent(self) -> None:
        root = _root()
        self.assertEqual(ensure_gitignore_rule(root), "added")
        self.assertEqual(ensure_gitignore_rule(root), "already-present")
        self.assertEqual((root / ".gitignore").read_text(encoding="utf-8").count(GITIGNORE_RULE), 1)


class PrivateTierIgnoredTests(unittest.TestCase):
    def test_dir_only_pattern_matches_probe_beneath_absent_directory(self) -> None:
        root = _git_root()
        (root / ".gitignore").write_text(f"{GITIGNORE_RULE}\n", encoding="utf-8")
        self.assertFalse(_local(root).exists())
        self.assertTrue(private_tier_ignored(root))

    def test_missing_rule_is_not_ignored(self) -> None:
        self.assertFalse(private_tier_ignored(_git_root()))


class EnsurePrivateTierTests(unittest.TestCase):
    def test_creates_every_seed_area_and_readme(self) -> None:
        root = _root()
        local = _local(root)
        result = ensure_private_tier(root, local)
        for area in PRIVATE_TIER_SEED:
            directory = local / area.path
            self.assertTrue(directory.is_dir(), area.path)
            self.assertTrue((directory / "README.md").is_file(), area.path)
        self.assertTrue((local / "README.md").is_file())
        self.assertTrue(result["created"])
        self.assertTrue(result["seeded"])

    def test_idempotent_and_does_not_overwrite_seed_file(self) -> None:
        root = _root()
        local = _local(root)
        ensure_private_tier(root, local)
        readme = local / "notes" / "README.md"
        readme.write_text("personal edit\n", encoding="utf-8")
        second = ensure_private_tier(root, local)
        self.assertEqual(readme.read_text(encoding="utf-8"), "personal edit\n")
        self.assertEqual(second["created"], [])
        self.assertEqual(second["seeded"], [])
        self.assertTrue(second["existing"])


if __name__ == "__main__":
    unittest.main()
