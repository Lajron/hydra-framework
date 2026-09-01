"""Mirror test for `hydra_engine.objects.moves`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.objects import moves  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402

FIELDS = dict(
    recorded_uid="u1",
    recorded_path="old/path.md",
    recorded_digest="sha256:aaa",
    current_uid="u1",
    current_path="new/path.md",
    current_digest="sha256:aaa",
    recorded_path_occupied=False,
)


def _paths(root: Path) -> ObjectLocations:
    return ObjectLocations(
        root=root,
        hydra=root / ".hydra-framework",
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=root / ".hydra-framework/cognition/graph/registry.yaml",
    )


class MoveClassificationTests(unittest.TestCase):
    def classify(self, **overrides) -> moves.MoveVerdict:
        return moves.classify_object_move(**{**FIELDS, **overrides})

    def test_same_uid_same_digest_new_path_is_unambiguous(self):
        self.assertEqual(self.classify().classification, moves.UNAMBIGUOUS_MOVE)

    def test_unchanged_path_is_not_a_move(self):
        verdict = self.classify(current_path=FIELDS["recorded_path"])
        self.assertEqual(verdict.classification, moves.NOT_A_MOVE)

    def test_missing_uid_on_either_side_is_ambiguous(self):
        self.assertEqual(self.classify(recorded_uid="").classification, moves.AMBIGUOUS_MOVE)
        self.assertEqual(self.classify(current_uid="").classification, moves.AMBIGUOUS_MOVE)

    def test_different_uid_is_not_a_move(self):
        self.assertEqual(self.classify(current_uid="u2").classification, moves.NOT_A_MOVE)

    def test_changed_digest_is_ambiguous(self):
        self.assertEqual(self.classify(current_digest="sha256:bbb").classification, moves.AMBIGUOUS_MOVE)

    def test_occupied_recorded_path_is_ambiguous(self):
        self.assertEqual(self.classify(recorded_path_occupied=True).classification, moves.AMBIGUOUS_MOVE)

    def test_every_reason_has_a_human_detail(self):
        for reason in moves.MOVE_REASONS:
            self.assertTrue(moves.MoveVerdict("", reason).detail())


class PathExistsFromRegistryTests(unittest.TestCase):
    def test_empty_value_does_not_exist(self):
        root = Path(tempfile.mkdtemp(prefix="moves-test-"))
        self.assertFalse(moves.path_exists_from_registry("", _paths(root)))

    def test_hydra_relative_path_resolves_against_root(self):
        root = Path(tempfile.mkdtemp(prefix="moves-test-"))
        target = root / ".hydra-framework" / "obj.md"
        target.parent.mkdir(parents=True)
        target.write_text("x", encoding="utf-8")
        self.assertTrue(moves.path_exists_from_registry(".hydra-framework/obj.md", _paths(root)))


if __name__ == "__main__":
    unittest.main()
