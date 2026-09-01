"""Unit tests for approval-state persistence, digest, and validation helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import config  # noqa: E402
from hydra_engine.intake import approval_state  # noqa: E402
from hydra_engine.intake.paths import IntakePaths  # noqa: E402


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="approval-state-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


class PathDigestTests(unittest.TestCase):
    def test_file_digest_changes_with_content(self):
        paths = _paths()
        path = paths.root / "a.txt"
        path.write_text("one", encoding="utf-8")
        first = approval_state.path_digest(path)
        path.write_text("two", encoding="utf-8")
        second = approval_state.path_digest(path)
        self.assertNotEqual(first, second)

    def test_directory_digest_reflects_child_names(self):
        paths = _paths()
        (paths.root / "child-a.txt").write_text("same", encoding="utf-8")
        first = approval_state.path_digest(paths.root)
        (paths.root / "child-a.txt").rename(paths.root / "child-b.txt")
        second = approval_state.path_digest(paths.root)
        self.assertNotEqual(first, second)

    def test_symlink_is_rejected(self):
        paths = _paths()
        target = paths.root / "real.txt"
        target.write_text("x", encoding="utf-8")
        link = paths.root / "link.txt"
        link.symlink_to(target)
        with self.assertRaises(ValueError):
            approval_state.path_digest(link)


class ValidationHelperTests(unittest.TestCase):
    def test_validate_capability_class_accepts_known_and_rejects_unknown(self):
        approval_state.validate_capability_class(config.CAPABILITY_CLASSES[0])
        with self.assertRaises(ValueError):
            approval_state.validate_capability_class("not-a-real-class")

    def test_reject_provider_specific_keys_walks_nested_structures(self):
        approval_state.reject_provider_specific_keys({"a": [{"b": "ok"}]})
        with self.assertRaises(ValueError):
            approval_state.reject_provider_specific_keys({"nested": {"model": "x"}})

    def test_validate_drafting_chain_requires_unique_non_empty_instances(self):
        chain = approval_state.validate_drafting_chain(["drafter-1"], default_capability_class="tool-heavy")
        self.assertEqual(chain, [{"instance": "drafter-1", "capability_class": "tool-heavy"}])
        with self.assertRaises(ValueError):
            approval_state.validate_drafting_chain(["drafter-1", "drafter-1"], default_capability_class="tool-heavy")


class ReconciliationAndGateTests(unittest.TestCase):
    def test_normalize_reconciliation_accepts_mapping_and_item_list(self):
        from_mapping = approval_state.normalize_reconciliation({"a": "promoted"})
        from_list = approval_state.normalize_reconciliation({"items": [{"path": "a", "status": "promoted"}]})
        self.assertEqual(from_mapping, from_list)

    def test_normalize_reconciliation_rejects_duplicate_items(self):
        with self.assertRaises(ValueError):
            approval_state.normalize_reconciliation(
                [{"path": "a", "status": "promoted"}, {"path": "a", "status": "rejected"}]
            )

    def test_gate_deduplicates_reasons_and_marks_pending(self):
        result = approval_state.gate("staging", 0, ["a", "a", "b"], {"k": "v"})
        self.assertEqual(result["reasons"], ["a", "b"])
        self.assertEqual(result["status"], "pending")

    def test_json_digest_is_key_order_independent(self):
        self.assertEqual(
            approval_state.json_digest({"a": 1, "b": 2}),
            approval_state.json_digest({"b": 2, "a": 1}),
        )


class ContainedRelativeTests(unittest.TestCase):
    def test_rejects_absolute_and_parent_escaping_paths(self):
        paths = _paths()
        with self.assertRaises(ValueError):
            approval_state.contained_relative(paths.root, "/etc/passwd", "path")
        with self.assertRaises(ValueError):
            approval_state.contained_relative(paths.root, "../outside", "path")

    def test_accepts_a_root_contained_relative_path(self):
        paths = _paths()
        resolved = approval_state.contained_relative(paths.root, "incoming/file.md", "path")
        self.assertEqual(resolved, paths.root / "incoming/file.md")

    def test_assert_expected_staging_path_rejects_paths_outside_the_route(self):
        paths = _paths()
        with self.assertRaises(ValueError):
            approval_state.assert_expected_staging_path(
                paths, "legacy-ai", "shared", paths.root / ".hydra-framework.local/migrations/legacy-ai/originals/x"
            )


class BatchStatePersistenceTests(unittest.TestCase):
    def test_save_and_load_round_trip_through_the_batch_state_file(self):
        paths = _paths()
        state = {
            "schema": approval_state.APPROVAL_SCHEMA,
            "slug": "legacy-ai",
            "batch": "package-batch",
            "workspace": ".hydra-framework/intake/migrations/2026-08-29-legacy-ai",
        }
        approval_state.save(paths, state)
        loaded = approval_state.load_batch(paths, "legacy-ai", "package-batch")
        self.assertEqual(loaded, state)

    def test_load_batch_raises_for_a_missing_batch(self):
        paths = _paths()
        with self.assertRaises(FileNotFoundError):
            approval_state.load_batch(paths, "legacy-ai", "package-batch")


if __name__ == "__main__":
    unittest.main()
