"""Synthetic-fixture tests for approval-aware migration batches."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.intake import approval  # noqa: E402
from hydra_engine.intake.paths import IntakePaths  # noqa: E402


def _paths() -> IntakePaths:
    root = Path(tempfile.mkdtemp(prefix="intake-approval-"))
    return IntakePaths(root=root, hydra=root / ".hydra-framework")


def _seed(paths: IntakePaths, rel: str, content: str) -> Path:
    path = paths.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _chain(instance: str = "drafter-1") -> list[dict]:
    return [{"instance": instance, "capability_class": "deep-reasoning"}]


def _request(paths: IntakePaths, sources: list[dict] | None = None) -> dict:
    sources = sources or [{"path": "incoming", "route": "shared"}]
    with mock.patch("hydra_engine.ports.clock.today", return_value="2026-08-29"):
        return approval.request_staging(
            paths,
            "legacy-ai",
            "package-batch",
            sources,
            drafting_chain=_chain(),
            capability_class="tool-heavy",
        )


def _proposal(paths: IntakePaths, state: dict, content: str = "# Migrated\n") -> tuple[dict, Path]:
    draft = paths.root / state["workspace"] / "batches/package-batch/drafts/state.md"
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(content, encoding="utf-8")
    source_items = [finding["path"] for item in state["source_items"] for finding in item["findings"]]
    result = approval.submit_proposal(
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
    return result, draft


def _evidence(state: dict, validator: str = "validator-1") -> dict:
    proposal = state["proposal"]
    return {
        "validator_instance": validator,
        "capability_class": "review-focused",
        "fresh_instance": True,
        "no_drafting_context": True,
        "proposal_digest": proposal["proposal_digest"],
        "target_digests": {unit["target_path"]: unit["target_digest"] for unit in proposal["units"]},
        "checks": [
            {"command": "hydra.py knowledge validate-package-docs synthetic-package", "exit_code": 0},
            {"command": "hydra.py ref check", "exit_code": 0},
        ],
    }


class ApprovalMigrationTests(unittest.TestCase):
    def test_full_approve_path_publishes_and_removes_only_exact_staged_roots(self):
        paths = _paths()
        _seed(paths, "incoming/guide.md", "# Legacy guide\n")
        _seed(paths, "secrets/.env", "TOKEN=synthetic-not-a-secret\n")
        state = _request(
            paths,
            [
                {"path": "incoming", "route": "shared"},
                {"path": "secrets", "route": "private"},
            ],
        )

        self.assertEqual(state["phase"], "awaiting-staging-approval")
        self.assertIn("sensitive-or-private-material", state["current_approval"]["reasons"])
        self.assertIn("ambiguous-git-status", state["current_approval"]["reasons"])
        self.assertEqual(len(state["current_approval"]["action"]["moves"]), 2)
        self.assertTrue((paths.root / "incoming/guide.md").is_file())

        state = approval.decide(paths, "legacy-ai", "package-batch", "approve", actor="human-1")
        self.assertEqual(state["phase"], "staged")
        self.assertFalse((paths.root / "incoming").exists())
        self.assertTrue((paths.root / ".migrations/legacy-ai/incoming/guide.md").is_file())
        self.assertTrue(
            (paths.root / ".hydra-framework.local/migrations/legacy-ai/originals/secrets/.env").is_file()
        )
        workspace = paths.root / state["workspace"]
        self.assertTrue((workspace / "README.md").is_file())
        self.assertTrue((workspace / "ledger.md").is_file())
        self.assertNotIn(
            ".hydra-framework.local/migrations/legacy-ai/originals/secrets",
            (workspace / "README.md").read_text(encoding="utf-8"),
        )

        state, _ = _proposal(paths, state)
        self.assertEqual(state["phase"], "awaiting-independent-validation")
        state = approval.record_validation(paths, "legacy-ai", "package-batch", _evidence(state))
        self.assertEqual(state["phase"], "awaiting-publication-approval")
        self.assertIn("new-package-boundary", state["current_approval"]["reasons"])
        self.assertEqual(
            state["current_approval"]["action"]["units"][0]["target_path"],
            ".hydra-framework/repo/knowledge/knowledge-packages/synthetic-package/state.md",
        )
        state = approval.decide(paths, "legacy-ai", "package-batch", "approve")
        target = paths.root / ".hydra-framework/repo/knowledge/knowledge-packages/synthetic-package/state.md"
        self.assertEqual(target.read_text(encoding="utf-8"), "# Migrated\n")

        # This was never part of the approved move and must survive closure.
        unrelated = _seed(paths, ".migrations/legacy-ai/unrelated.md", "retain\n")
        statuses = {
            "incoming/guide.md": "promoted",
            "secrets/.env": "kept-private",
        }
        state = approval.request_closure(paths, "legacy-ai", "package-batch", statuses)
        self.assertEqual(state["phase"], "awaiting-closure-approval")
        state = approval.decide(paths, "legacy-ai", "package-batch", "approve")
        self.assertEqual(state["phase"], "closed")
        self.assertFalse((paths.root / ".migrations/legacy-ai/incoming").exists())
        self.assertFalse(
            (paths.root / ".hydra-framework.local/migrations/legacy-ai/originals/secrets").exists()
        )
        self.assertTrue(unrelated.is_file())
        self.assertTrue((workspace / "batches/package-batch/state.json").is_file())
        ledger_text = (workspace / "ledger.md").read_text(encoding="utf-8")
        self.assertIn("Status: complete", ledger_text)
        self.assertIn("- Terminal: 2", ledger_text)
        self.assertIn("- Pending: 0", ledger_text)
        self.assertNotIn("secrets/.env", ledger_text)

    def test_reject_is_terminal_and_does_not_move_source(self):
        paths = _paths()
        source = _seed(paths, "incoming/file.md", "content\n")
        _request(paths)

        state = approval.decide(
            paths,
            "legacy-ai",
            "package-batch",
            "reject",
            rationale="Not in migration scope",
        )

        self.assertEqual(state["phase"], "rejected")
        self.assertTrue(source.is_file())
        self.assertEqual(state["history"][-1]["rationale"], "Not in migration scope")
        with self.assertRaises(ValueError):
            approval.decide(paths, "legacy-ai", "package-batch", "approve")

    def test_revise_reuses_batch_and_requires_new_validation(self):
        paths = _paths()
        _seed(paths, "incoming/file.md", "content\n")
        _request(paths)
        state = approval.decide(paths, "legacy-ai", "package-batch", "approve")
        state, draft = _proposal(paths, state, "# First\n")
        first_digest = state["proposal"]["proposal_digest"]
        state = approval.record_validation(paths, "legacy-ai", "package-batch", _evidence(state))

        state = approval.decide(
            paths,
            "legacy-ai",
            "package-batch",
            "revise",
            guidance="Clarify the package summary",
        )
        self.assertEqual(state["phase"], "publication-revision-required")
        self.assertEqual(state["revision"], 1)
        self.assertIsNone(state["validation"])
        draft.write_text("# Revised\n", encoding="utf-8")
        state, _ = _proposal(paths, state, "# Revised\n")
        with self.assertRaisesRegex(ValueError, "fresh for every canonical proposal"):
            approval.record_validation(paths, "legacy-ai", "package-batch", _evidence(state, "validator-1"))
        stale = _evidence(state, "validator-2")
        stale["proposal_digest"] = first_digest
        with self.assertRaisesRegex(ValueError, "proposal digest"):
            approval.record_validation(paths, "legacy-ai", "package-batch", stale)
        state = approval.record_validation(paths, "legacy-ai", "package-batch", _evidence(state, "validator-2"))
        state = approval.decide(paths, "legacy-ai", "package-batch", "approve")
        self.assertEqual(state["phase"], "published")

    def test_validator_must_be_independent(self):
        paths = _paths()
        _seed(paths, "incoming/file.md", "content\n")
        _request(paths)
        state = approval.decide(paths, "legacy-ai", "package-batch", "approve")
        state, _ = _proposal(paths, state)

        with self.assertRaisesRegex(ValueError, "differ from every drafting-chain"):
            approval.record_validation(paths, "legacy-ai", "package-batch", _evidence(state, "drafter-1"))

    def test_publication_refuses_digest_drift(self):
        paths = _paths()
        _seed(paths, "incoming/file.md", "content\n")
        _request(paths)
        state = approval.decide(paths, "legacy-ai", "package-batch", "approve")
        state, draft = _proposal(paths, state)
        approval.record_validation(paths, "legacy-ai", "package-batch", _evidence(state))
        draft.write_text("changed after validation\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "draft drift"):
            approval.decide(paths, "legacy-ai", "package-batch", "approve")
        self.assertFalse(
            (paths.root / ".hydra-framework/repo/knowledge/knowledge-packages/synthetic-package/state.md").exists()
        )

    def test_close_refuses_unreconciled_items(self):
        paths = _paths()
        _seed(paths, "incoming/one.md", "one\n")
        _seed(paths, "incoming/two.md", "two\n")
        _request(paths)
        state = approval.decide(paths, "legacy-ai", "package-batch", "approve")
        state, _ = _proposal(paths, state)
        state = approval.record_validation(paths, "legacy-ai", "package-batch", _evidence(state))
        approval.decide(paths, "legacy-ai", "package-batch", "approve")

        with self.assertRaisesRegex(ValueError, "unreconciled"):
            approval.request_closure(
                paths,
                "legacy-ai",
                "package-batch",
                {"incoming/one.md": "promoted"},
            )
        self.assertTrue((paths.root / ".migrations/legacy-ai/incoming/two.md").is_file())

    def test_provider_keys_and_invalid_capability_classes_are_rejected(self):
        paths = _paths()
        _seed(paths, "incoming/file.md", "content\n")
        with self.assertRaisesRegex(ValueError, "unknown capability"):
            approval.request_staging(
                paths,
                "legacy-ai",
                "package-batch",
                [{"path": "incoming", "route": "shared"}],
                drafting_chain=_chain(),
                capability_class="specific-model",
            )
        state = _request(paths)
        approval.decide(paths, "legacy-ai", "package-batch", "approve")
        draft = paths.root / state["workspace"] / "batches/package-batch/drafts/state.md"
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_text("# Draft\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "provider-neutral"):
            approval.submit_proposal(
                paths,
                "legacy-ai",
                "package-batch",
                {
                    "package_slug": "synthetic-package",
                    "provider": "fixed-provider",
                    "units": [
                        {
                            "draft_path": draft.relative_to(paths.root).as_posix(),
                            "target_path": ".hydra-framework/repo/knowledge/knowledge-packages/synthetic-package/state.md",
                        }
                    ],
                },
            )


if __name__ == "__main__":
    unittest.main()
