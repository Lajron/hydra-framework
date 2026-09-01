"""B1 merge regression:
`generated_at`/`generated_by` changed on every regeneration, so any two
branches that both ran `ref index` conflicted on that line whether or not
their real changes overlapped. This proves two branches that each add a
different object now merge without conflict."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.objects import discovery, registry  # noqa: E402

_UID_A = "11111111-1111-4111-8111-111111111111"
_UID_M = "22222222-2222-4222-8222-222222222222"
_UID_Z = "33333333-3333-4333-8333-333333333333"


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _git_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="merge-regression-"))
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Hydra Test"], root)
    return root


def _paths(root: Path) -> discovery.ObjectLocations:
    hydra = root / ".hydra-framework"
    return discovery.ObjectLocations(
        root=root, hydra=hydra, local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml",
    )


def _add_object(paths: discovery.ObjectLocations, rel: str, hydra_id: str, uid: str) -> None:
    path = paths.hydra / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"hydra_id: {hydra_id}\n"
        f"uid: {uid}\n"
        "schema_version: 3\n"
        "kind: knowledge-unit\n"
        "title: Fixture\n"
        "status: active\n"
        "scope: repo\n"
        "owners:\n  team: fixture\n"
        "relations: []\n"
        "provenance:\n  sources: []\n"
        "---\n# Fixture\n",
        encoding="utf-8",
    )


def _commit(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", message], root)


class MergeRegressionTests(unittest.TestCase):
    def test_two_branches_adding_different_objects_merge_without_conflict(self):
        # The two additions sort to opposite ends of the file (`a` before
        # the base object, `z` after it), well clear of each other and of
        # the base object's own ~13-line block, so this isolates the fix
        # (no more shared, always-changing `generated_at` line) from git's
        # unrelated tendency to conflict on two insertions at the same
        # adjacent line.
        root = _git_repo()
        paths = _paths(root)
        _add_object(paths, "knowledge-units/0005-m.md", "hydra://knowledge-unit/0005-m", _UID_M)
        registry.write_object_registry(paths)
        _commit(root, "base")

        _run(["git", "checkout", "-q", "-b", "add-a"], root)
        _add_object(paths, "knowledge-units/0001-a.md", "hydra://knowledge-unit/0001-a", _UID_A)
        registry.write_object_registry(paths)
        _commit(root, "add a")

        _run(["git", "checkout", "-q", "main"], root)
        _add_object(paths, "knowledge-units/0009-z.md", "hydra://knowledge-unit/0009-z", _UID_Z)
        registry.write_object_registry(paths)
        _commit(root, "add z")

        result = subprocess.run(
            ["git", "merge-tree", "--write-tree", "main", "add-a"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"stdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertNotIn("CONFLICT", result.stdout)


if __name__ == "__main__":
    unittest.main()
