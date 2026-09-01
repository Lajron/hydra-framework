"""Unit tests for approval-actions: inventorying sources and applying gates."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.intake import approval as approval_module  # noqa: E402
from hydra_engine.intake import approval_actions  # noqa: E402
from hydra_engine.intake import approval_state  # noqa: E402
from hydra_engine.intake.paths import IntakePaths  # noqa: E402


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="approval-actions-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


def _seed(paths: IntakePaths, rel: str, content: str) -> Path:
    path = paths.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _staged_state(paths: IntakePaths, sources: list[dict] | None = None) -> dict:
    sources = sources or [{"path": "incoming", "route": "shared"}]
    with mock.patch("hydra_engine.ports.clock.today", return_value="2026-08-29"):
        return approval_module.request_staging(
            paths,
            "legacy-ai",
            "package-batch",
            sources,
            drafting_chain=[{"instance": "drafter-1", "capability_class": "deep-reasoning"}],
            capability_class="tool-heavy",
        )


def _validated_state(paths: IntakePaths) -> dict:
    """Drive a staged batch through propose + independent validation."""
    state = _staged_state(paths)
    approval_actions.apply_staging(paths, state)
    approval_state.save(paths, state)
    draft = paths.root / state["workspace"] / "batches/package-batch/drafts/state.md"
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text("# Migrated\n", encoding="utf-8")
    source_items = [finding["path"] for item in state["source_items"] for finding in item["findings"]]
    state = approval_module.submit_proposal(
        paths,
        "legacy-ai",
        "package-batch",
        {
            "package_slug": "synthetic-package",
            "units": [
                {
                    "draft_path": draft.relative_to(paths.root).as_posix(),
                    "target_path": ".hydra-framework/repo/knowledge/knowledge-packages/synthetic-package/state.md",
                    "source_items": source_items,
                }
            ],
        },
    )
    return approval_module.record_validation(
        paths,
        "legacy-ai",
        "package-batch",
        {
            "validator_instance": "validator-1",
            "capability_class": "review-focused",
            "fresh_instance": True,
            "no_drafting_context": True,
            "proposal_digest": state["proposal"]["proposal_digest"],
            "target_digests": {unit["target_path"]: unit["target_digest"] for unit in state["proposal"]["units"]},
            "checks": [
                {"command": "hydra.py knowledge validate-package-docs synthetic-package", "exit_code": 0},
                {"command": "hydra.py ref check", "exit_code": 0},
            ],
        },
    )


class InventorySourcesTests(unittest.TestCase):
    def test_shared_source_is_staged_under_the_shared_route(self):
        paths = _paths()
        _seed(paths, "incoming/file.md", "hello\n")

        items = approval_actions.inventory_sources(paths, "legacy-ai", [{"path": "incoming", "route": "shared"}])

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["planned_staged_path"], ".migrations/legacy-ai/incoming")
        self.assertEqual(items[0]["files"], 1)

    def test_private_source_uses_the_private_originals_route(self):
        paths = _paths()
        _seed(paths, "secrets/.env", "TOKEN=synthetic-not-a-secret\n")

        items = approval_actions.inventory_sources(paths, "legacy-ai", [{"path": "secrets", "route": "private"}])

        self.assertEqual(
            items[0]["planned_staged_path"], ".hydra-framework.local/migrations/legacy-ai/originals/secrets"
        )

    def test_duplicate_destinations_are_rejected(self):
        paths = _paths()
        _seed(paths, "one/shared/file.md", "a\n")
        _seed(paths, "two/shared/file.md", "b\n")

        with self.assertRaisesRegex(ValueError, "multiple sources map to the same staging target"):
            approval_actions.inventory_sources(
                paths,
                "legacy-ai",
                [{"path": "one/shared", "route": "shared"}, {"path": "two/shared", "route": "shared"}],
            )

    def test_symlinked_source_root_is_rejected(self):
        paths = _paths()
        target = _seed(paths, "real/file.md", "content\n")
        link = paths.root / "linked"
        link.symlink_to(target.parent)

        with self.assertRaisesRegex(ValueError, "may not be symbolic links"):
            approval_actions.inventory_sources(paths, "legacy-ai", [{"path": "linked", "route": "shared"}])


class ApplyStagingTests(unittest.TestCase):
    def test_apply_staging_moves_source_and_writes_workspace_docs(self):
        paths = _paths()
        _seed(paths, "incoming/file.md", "hello\n")
        state = _staged_state(paths)

        approval_actions.apply_staging(paths, state)

        self.assertEqual(state["phase"], "staged")
        self.assertFalse((paths.root / "incoming").exists())
        self.assertTrue((paths.root / ".migrations/legacy-ai/incoming/file.md").is_file())
        workspace = approval_state.contained_relative(paths.root, state["workspace"], "workspace")
        self.assertTrue((workspace / "README.md").is_file())
        self.assertTrue((workspace / "ledger.md").is_file())


class ApplyPublicationTests(unittest.TestCase):
    def test_apply_publication_writes_target_and_detects_drift(self):
        paths = _paths()
        _seed(paths, "incoming/file.md", "hello\n")
        state = _validated_state(paths)
        draft = paths.root / state["proposal"]["units"][0]["draft_path"]

        approval_actions.apply_publication(paths, state)
        self.assertEqual(state["phase"], "published")
        target = paths.root / ".hydra-framework/repo/knowledge/knowledge-packages/synthetic-package/state.md"
        self.assertEqual(target.read_text(encoding="utf-8"), "# Migrated\n")

        draft.write_text("changed after validation\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "draft drift"):
            approval_actions.apply_publication(paths, state)


class ApplyClosureTests(unittest.TestCase):
    def test_apply_closure_removes_exact_paths_and_writes_a_reconciled_ledger(self):
        paths = _paths()
        _seed(paths, "incoming/file.md", "hello\n")
        state = _validated_state(paths)
        approval_actions.apply_publication(paths, state)
        approval_state.save(paths, state)
        source_items = [finding["path"] for item in state["source_items"] for finding in item["findings"]]
        state = approval_module.request_closure(
            paths, "legacy-ai", "package-batch", {item: "promoted" for item in source_items}
        )

        approval_actions.apply_closure(paths, state)

        self.assertEqual(state["phase"], "closed")
        self.assertFalse((paths.root / ".migrations/legacy-ai/incoming").exists())
        workspace = approval_state.contained_relative(paths.root, state["workspace"], "workspace")
        ledger_text = (workspace / "ledger.md").read_text(encoding="utf-8")
        self.assertIn("## Status Values", ledger_text)
        self.assertIn("- `promoted`: durable meaning is under a canonical owner", ledger_text)


class ReconciledLedgerTextAndStatusMentionsTests(unittest.TestCase):
    def test_reconciled_ledger_text_groups_private_items_without_naming_them(self):
        state = {
            "slug": "legacy-ai",
            "proposal": None,
            "source_items": [
                {
                    "route": "private",
                    "findings": [{"path": "secrets/.env", "classifications": ["private-hydra-risk"]}],
                }
            ],
            "reconciliation": {"items": [{"path": "secrets/.env", "status": "kept-private"}]},
        }
        text = approval_actions.reconciled_ledger_text(state)
        self.assertNotIn("secrets/.env", text)
        self.assertIn("private staged items (1)", text)

    def test_status_mentions_matches_exact_path_and_directory_prefix(self):
        self.assertTrue(approval_actions.status_mentions("?? incoming/file.md", "incoming/file.md"))
        self.assertTrue(approval_actions.status_mentions("?? incoming/", "incoming"))
        self.assertFalse(approval_actions.status_mentions("?? other/file.md", "incoming"))


if __name__ == "__main__":
    unittest.main()
