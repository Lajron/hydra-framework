"""intake-cluster goldens: migration inventory, migration ledger."""

from __future__ import annotations

import unittest
from pathlib import Path

from .fixtures import assert_golden, run_golden
from hydra_engine.intake import approval
from hydra_engine.intake.paths import IntakePaths


def _prepare_closure_request(root: Path) -> None:
    paths = IntakePaths(root=root, hydra=root / ".hydra-framework")
    state = approval.request_staging(
        paths,
        "demo-slug",
        "package-batch",
        [{"path": "incoming", "route": "shared"}],
        drafting_chain=[{"instance": "drafter-1", "capability_class": "deep-reasoning"}],
        capability_class="tool-heavy",
    )
    state = approval.decide(paths, "demo-slug", "package-batch", "approve", actor="reviewer")
    draft = root / state["workspace"] / "batches/package-batch/drafts/state.md"
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text("# Synthetic package state\n", encoding="utf-8")
    source_items = [finding["path"] for item in state["source_items"] for finding in item["findings"]]
    state = approval.submit_proposal(
        paths,
        "demo-slug",
        "package-batch",
        {
            "package_slug": "synthetic-package",
            "units": [
                {
                    "draft_path": draft.relative_to(root).as_posix(),
                    "target_path": ".hydra-framework/repo/knowledge/knowledge-packages/synthetic-package/state.md",
                    "source_items": source_items,
                }
            ],
        },
    )
    proposal = state["proposal"]
    evidence = {
        "validator_instance": "validator-1",
        "capability_class": "review-focused",
        "fresh_instance": True,
        "no_drafting_context": True,
        "proposal_digest": proposal["proposal_digest"],
        "target_digests": {unit["target_path"]: unit["target_digest"] for unit in proposal["units"]},
        "checks": [
            {"command": "hydra.py validate-package-docs --path <proposal>", "exit_code": 0},
            {"command": "hydra.py ref check", "exit_code": 0},
        ],
    }
    state = approval.record_validation(paths, "demo-slug", "package-batch", evidence)
    approval.decide(paths, "demo-slug", "package-batch", "approve", actor="reviewer")
    approval.request_closure(
        paths,
        "demo-slug",
        "package-batch",
        {source_item: "promoted" for source_item in source_items},
    )


class IntakeGoldenTests(unittest.TestCase):
    def test_migration_inventory_happy_path(self):
        outcome = run_golden(["migration", "inventory"], extra_fixture={".migrations/demo-slug/file.txt": "hello\n"})
        assert_golden(self, "intake-migration-inventory", outcome)

    def test_migration_ledger_happy_path(self):
        outcome = run_golden(
            ["migration", "ledger", "demo-slug", "--create"],
            extra_fixture={".migrations/demo-slug/file.txt": "hello\n"},
        )
        assert_golden(self, "intake-migration-ledger", outcome)

    def test_migration_inventory_json(self):
        outcome = run_golden(
            ["migration", "inventory", "--json"],
            extra_fixture={".migrations/demo-slug/file.txt": "hello\n"},
        )
        assert_golden(self, "intake-migration-inventory-json", outcome)

    def test_migration_inventory_unknown_slug(self):
        outcome = run_golden(
            ["migration", "inventory", "nope"],
            extra_fixture={".migrations/demo-slug/file.txt": "hello\n"},
        )
        assert_golden(self, "intake-migration-inventory-unknown-slug", outcome)

    def test_migration_ledger_status_without_create(self):
        outcome = run_golden(
            ["migration", "ledger", "demo-slug"],
            extra_fixture={".migrations/demo-slug/file.txt": "hello\n"},
        )
        assert_golden(self, "intake-migration-ledger-status", outcome)

    def test_migration_ledger_already_exists_refusal(self):
        outcome = run_golden(
            ["migration", "ledger", "demo-slug", "--create"],
            extra_fixture={
                ".migrations/demo-slug/file.txt": "hello\n",
                ".hydra-framework/intake/migrations/2026-01-01-demo-slug/ledger.md": "# existing\n",
            },
        )
        assert_golden(self, "intake-migration-ledger-already-exists", outcome)

    def test_migration_ledger_unknown_slug_refusal(self):
        outcome = run_golden(
            ["migration", "ledger", "nope", "--create"],
            extra_fixture={".migrations/demo-slug/file.txt": "hello\n"},
        )
        assert_golden(self, "intake-migration-ledger-unknown-slug", outcome)

    def test_migration_request_stage_records_a_bounded_approval(self):
        outcome = run_golden(
            [
                "migration", "request-stage", "demo-slug", "package-batch",
                "--source", "incoming", "--route", "shared",
                "--worker-instance", "drafter-1", "--capability-class", "tool-heavy", "--json",
            ],
            extra_fixture={"incoming/file.md": "synthetic source\n"},
        )
        assert_golden(self, "intake-migration-request-stage-json", outcome)

    def test_migration_close_approval_removes_only_synthetic_staged_originals(self):
        outcome = run_golden(
            ["migration", "decide", "demo-slug", "package-batch", "approve", "--json"],
            extra_fixture={"incoming/file.md": "synthetic source\n"},
            pre_run=_prepare_closure_request,
        )
        assert_golden(self, "intake-migration-close-approve-json", outcome)


if __name__ == "__main__":
    unittest.main()
