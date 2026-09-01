"""Mirror test for `hydra_engine.commands.private_tier`."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.agent_hooks.token_budget import DEFAULT_TOKEN_HOOK_POLICY  # noqa: E402
from hydra_engine.commands import private_tier  # noqa: E402
from hydra_engine.installation.paths import InstallationPaths  # noqa: E402
from hydra_engine.installation.private_tier import GITIGNORE_RULE  # noqa: E402


def _paths() -> InstallationPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-private-tier-"))
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    return InstallationPaths(root=root, hydra=root / ".hydra-framework")


def _run(args: argparse.Namespace, paths: InstallationPaths):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        result = private_tier.command_init_local(args, paths)
    return result, stdout.getvalue()


class CommandInitLocalTests(unittest.TestCase):
    def test_check_exits_one_when_rule_is_missing(self) -> None:
        paths = _paths()
        result, output = _run(argparse.Namespace(check=True, write_token_policy=False), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("gitignore rule: missing", output)

    def test_check_exits_zero_when_rule_is_present_and_effective(self) -> None:
        paths = _paths()
        (paths.root / ".gitignore").write_text(f"{GITIGNORE_RULE}\n", encoding="utf-8")
        result, output = _run(argparse.Namespace(check=True, write_token_policy=False), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("private tier ignored: yes", output)

    def test_write_token_policy_serializes_default_policy(self) -> None:
        paths = _paths()
        result, output = _run(argparse.Namespace(check=False, write_token_policy=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("token hook policy: written", output)
        policy = json.loads((paths.root / GITIGNORE_RULE.rstrip("/") / "monitoring" / "token-hooks.json").read_text())
        self.assertEqual(policy, DEFAULT_TOKEN_HOOK_POLICY)


if __name__ == "__main__":
    unittest.main()
