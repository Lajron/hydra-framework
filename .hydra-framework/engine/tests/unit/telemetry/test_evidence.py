"""Mirror test for `hydra_engine.telemetry.evidence`."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.telemetry import evidence  # noqa: E402

# The real `.hydra-framework/` tree, so `redaction_digest()` has a real
# `telemetry/redaction.py` to hash. `telemetry_evidence_notes` computes it
# lazily -- only when an `open` package's attestation actually needs
# comparing -- so a temp `root` is fine everywhere else in this file.
_HYDRA = _SRC.parent.parent


def _dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="telemetry-evidence-"))


def _overview_text(
    *,
    dir_name: str,
    status: str = "open",
    author: str = "dana",
    created: str = "2026-08-20",
    superseded_by: str = "",
    absorption: str = "TODO",
) -> str:
    lines = [
        "---",
        f"hydra_id: hydra://telemetry-evidence/{dir_name}",
        "uid: 11111111-1111-1111-1111-111111111111",
        "schema_version: 3",
        "kind: telemetry-evidence",
        "title: Example Package",
        f"status: {status}",
        "scope: base-seed",
        "owners:",
        f"  individual: {author}",
        "relations:",
        "  - hydra://knowledge-unit/telemetry-as-first-class-evidence",
    ]
    if superseded_by:
        lines.append(f"superseded_by: hydra://telemetry-evidence/{superseded_by}")
    lines += [
        "provenance:",
        "  sources:",
        f"    - .hydra-framework/repo/telemetry/packages/{dir_name}/gate-attestation.json",
        "---",
        "",
        "# Example Package",
        "",
        f"Author: {author}",
        f"Created: {created}",
        "Window: 2026-08-01 to 2026-08-20",
        "Corpus: 10 events across 3 kinds",
        "",
        "## Question",
        "",
        "Does this reducer see enough coverage?",
        "",
        "## Findings",
        "",
        "10 events measured; 3 distinct kinds.",
        "",
        "## Method",
        "",
        "`hydra.py telemetry report --json`.",
        "",
        "## Absorption",
        "",
        absorption,
        "",
    ]
    return "\n".join(lines)


def _metrics(**overrides) -> dict:
    base = {
        "generated_at": "2026-08-28T00:00:00Z",
        "event_count": 10,
        "counts_by_kind": {"session.aggregate": 6, "command.invocation": 4},
        "field_names": ["at", "event_kind"],
    }
    base.update(overrides)
    return base


def _attestation(**overrides) -> dict:
    base = {
        "verdict": "pass",
        "date": "2026-08-28",
        "event_count": 10,
        "distinct_event_kinds": ["a", "b", "c"],
        "distinct_field_names": ["x", "y"],
        "redaction_digest": "deadbeef",
        "spillover_per_1000": 0,
        "failures": [],
    }
    base.update(overrides)
    return base


def _write_package(
    packages_dir: Path,
    dir_name: str,
    *,
    overview: str | None = None,
    metrics: dict | None = "default",
    attestation: dict | None = "default",
    extra_files: dict[str, str] | None = None,
) -> Path:
    package_dir = packages_dir / dir_name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "overview.md").write_text(
        overview if overview is not None else _overview_text(dir_name=dir_name), encoding="utf-8"
    )
    if metrics != "omit":
        (package_dir / "metrics.json").write_text(
            json.dumps(_metrics() if metrics == "default" else metrics), encoding="utf-8"
        )
    if attestation != "omit":
        (package_dir / "gate-attestation.json").write_text(
            json.dumps(_attestation() if attestation == "default" else attestation), encoding="utf-8"
        )
    for name, content in (extra_files or {}).items():
        (package_dir / name).write_text(content, encoding="utf-8")
    return package_dir


_VALID_DIR = "2026-08-20-dana-reducer-coverage"


class ValidatePackageTests(unittest.TestCase):
    def test_valid_package_passes(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR)
        findings = evidence.validate_package(package_dir, root)
        self.assertEqual(findings, [], [f.detail for f in findings])

    def test_missing_file_is_reported(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, metrics="omit")
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("metrics.json" in f.detail for f in findings))

    def test_unexpected_file_is_reported(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, extra_files={"evidence.md": "extra"})
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("unexpected entry" in f.detail for f in findings))

    def test_subdirectory_is_reported(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR)
        (package_dir / "units").mkdir()
        # `units` is also not one of the required files, so re-glob after adding it.
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("subdirectory" in f.detail for f in findings))

    def test_directory_name_must_start_with_date(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, "not-a-date-dana-x", overview=_overview_text(dir_name="not-a-date-dana-x"))
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("YYYY-MM-DD" in f.detail for f in findings))

    def test_created_must_match_directory_date(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(
            packages_dir, _VALID_DIR, overview=_overview_text(dir_name=_VALID_DIR, created="2026-08-19")
        )
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("does not match directory date" in f.detail for f in findings))

    def test_author_must_match_directory_owner_segment(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(
            packages_dir, _VALID_DIR, overview=_overview_text(dir_name=_VALID_DIR, author="not-dana")
        )
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("<Created>-<Author>-<short-slug>" in f.detail for f in findings))

    def test_hydra_id_must_match_directory_name(self):
        root = _dir()
        packages_dir = root / "packages"
        overview = _overview_text(dir_name=_VALID_DIR).replace(_VALID_DIR, "2026-08-20-dana-other", 1)
        package_dir = _write_package(packages_dir, _VALID_DIR, overview=overview)
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("hydra_id` must be" in f.detail for f in findings))

    def test_unknown_status_is_rejected(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, overview=_overview_text(dir_name=_VALID_DIR, status="in-review"))
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("`status` must be one of" in f.detail for f in findings))

    def test_superseded_without_pointer_fails(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, overview=_overview_text(dir_name=_VALID_DIR, status="superseded"))
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("requires `superseded_by`" in f.detail for f in findings))

    def test_superseded_with_pointer_passes(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(
            packages_dir, _VALID_DIR,
            overview=_overview_text(dir_name=_VALID_DIR, status="superseded", superseded_by="2026-08-25-dana-later"),
        )
        findings = evidence.validate_package(package_dir, root)
        self.assertEqual(findings, [])

    def test_superseded_by_without_superseded_status_fails(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(
            packages_dir, _VALID_DIR,
            overview=_overview_text(dir_name=_VALID_DIR, status="open", superseded_by="2026-08-25-dana-later"),
        )
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("not `superseded`" in f.detail for f in findings))

    def test_absorbed_with_todo_absorption_fails(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, overview=_overview_text(dir_name=_VALID_DIR, status="absorbed", absorption="TODO"))
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("requires `## Absorption`" in f.detail for f in findings))

    def test_absorbed_naming_an_artifact_passes(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(
            packages_dir, _VALID_DIR,
            overview=_overview_text(dir_name=_VALID_DIR, status="absorbed", absorption="Fed into repo/knowledge/reducer-coverage.md."),
        )
        findings = evidence.validate_package(package_dir, root)
        self.assertEqual(findings, [])

    def test_private_path_in_overview_fails(self):
        root = _dir()
        packages_dir = root / "packages"
        overview = _overview_text(dir_name=_VALID_DIR).replace(
            "10 events measured; 3 distinct kinds.",
            "See .hydra-framework.local/telemetry/events.jsonl for detail.",
        )
        package_dir = _write_package(packages_dir, _VALID_DIR, overview=overview)
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("private-tier path" in f.detail for f in findings))

    def test_unsafe_content_in_overview_fails(self):
        root = _dir()
        packages_dir = root / "packages"
        overview = _overview_text(dir_name=_VALID_DIR).replace(
            "10 events measured; 3 distinct kinds.",
            "tenant: restricted example saw this failure.",
        )
        package_dir = _write_package(packages_dir, _VALID_DIR, overview=overview)
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("unsafe content" in f.detail for f in findings))

    def test_raw_event_row_in_metrics_is_rejected(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(
            packages_dir, _VALID_DIR,
            metrics={"event_schema": "hydra.telemetry.event.v1", "event_kind": "command.invocation"},
        )
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("event_schema" in f.detail for f in findings))

    def test_array_of_objects_in_metrics_is_rejected(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, metrics={"rows": [{"a": 1}]})
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("holds objects" in f.detail or "unknown aggregate bucket" in f.detail for f in findings))

    def test_unknown_metrics_key_is_rejected(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, metrics={"mystery_bucket": 1})
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("unknown aggregate bucket" in f.detail for f in findings))

    def test_corpus_event_count_mismatch_is_rejected(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, metrics=_metrics(event_count=11))
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("Corpus:` states 10 events but metrics.json's `event_count` is 11" in f.detail for f in findings))

    def test_corpus_kind_count_mismatch_is_rejected(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, metrics=_metrics(distinct_event_kinds=4))
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("Corpus:` states 3 kinds but metrics.json's `distinct_event_kinds` is 4" in f.detail for f in findings))

    def test_corpus_matching_metrics_passes(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, metrics=_metrics(distinct_event_kinds=3))
        findings = evidence.validate_package(package_dir, root)
        self.assertEqual(findings, [])

    def test_corpus_in_unrecognized_shape_is_not_checked(self):
        root = _dir()
        packages_dir = root / "packages"
        overview = _overview_text(dir_name=_VALID_DIR).replace(
            "Corpus: 10 events across 3 kinds", "Corpus: about a dozen events, several kinds"
        )
        package_dir = _write_package(packages_dir, _VALID_DIR, overview=overview, metrics=_metrics(event_count=999))
        findings = evidence.validate_package(package_dir, root)
        self.assertFalse(any("Corpus:` states" in f.detail for f in findings))

    def test_failing_attestation_is_rejected(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, attestation=_attestation(verdict="fail"))
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("not `pass`" in f.detail for f in findings))

    def test_attestation_missing_keys_is_rejected(self):
        root = _dir()
        packages_dir = root / "packages"
        package_dir = _write_package(packages_dir, _VALID_DIR, attestation={"verdict": "pass"})
        findings = evidence.validate_package(package_dir, root)
        self.assertTrue(any("missing attestation field" in f.detail for f in findings))


class ValidateTelemetryEvidenceQueueTests(unittest.TestCase):
    def test_absent_directory_is_valid(self):
        root = _dir()
        self.assertEqual(evidence.validate_telemetry_evidence_queue(root / "packages", root), [])

    def test_valid_package_in_a_real_directory_passes(self):
        root = _dir()
        packages_dir = root / "packages"
        _write_package(packages_dir, _VALID_DIR)
        self.assertEqual(evidence.validate_telemetry_evidence_queue(packages_dir, root), [])

    def test_gitkeep_file_is_not_scanned_as_a_package(self):
        root = _dir()
        packages_dir = root / "packages"
        packages_dir.mkdir(parents=True)
        (packages_dir / ".gitkeep").write_text("", encoding="utf-8")
        self.assertEqual(evidence.validate_telemetry_evidence_queue(packages_dir, root), [])


class TelemetryEvidenceNotesTests(unittest.TestCase):
    def test_absent_directory_is_silent(self):
        root = _dir()
        self.assertEqual(evidence.telemetry_evidence_notes(root / "packages", root, _HYDRA, "2026-08-28"), [])

    def test_fresh_open_package_is_silent(self):
        root = _dir()
        packages_dir = root / "packages"
        _write_package(packages_dir, _VALID_DIR, overview=_overview_text(dir_name=_VALID_DIR, created="2026-08-25"))
        notes = evidence.telemetry_evidence_notes(packages_dir, root, _HYDRA, "2026-08-28")
        self.assertEqual([n for n in notes if "drain expectation" in n], [])

    def test_stale_open_package_produces_a_note(self):
        root = _dir()
        packages_dir = root / "packages"
        old_dir = "2026-01-01-dana-reducer-coverage"
        _write_package(packages_dir, old_dir, overview=_overview_text(dir_name=old_dir, created="2026-01-01"))
        notes = evidence.telemetry_evidence_notes(packages_dir, root, _HYDRA, "2026-08-28")
        self.assertTrue(any("drain expectation" in n for n in notes))

    def test_terminal_status_is_never_flagged_regardless_of_age(self):
        root = _dir()
        packages_dir = root / "packages"
        old_dir = "2026-01-01-dana-reducer-coverage"
        _write_package(
            packages_dir, old_dir,
            overview=_overview_text(dir_name=old_dir, created="2026-01-01", status="rejected", absorption="Not actionable."),
        )
        notes = evidence.telemetry_evidence_notes(packages_dir, root, _HYDRA, "2026-08-28")
        self.assertEqual(notes, [])

    def test_depth_note_fires_above_threshold(self):
        root = _dir()
        packages_dir = root / "packages"
        for index in range(3):
            dir_name = f"2026-08-2{index}-dana-question-{index}"
            _write_package(packages_dir, dir_name, overview=_overview_text(dir_name=dir_name, created=f"2026-08-2{index}"))
        notes = evidence.telemetry_evidence_notes(packages_dir, root, _HYDRA, "2026-08-28", depth_note=2)
        self.assertTrue(any("readability backstop" in n for n in notes))

    def test_digest_drift_produces_a_note(self):
        root = _dir()
        packages_dir = root / "packages"
        _write_package(packages_dir, _VALID_DIR, attestation=_attestation(redaction_digest="stale-digest"))
        notes = evidence.telemetry_evidence_notes(packages_dir, root, _HYDRA, "2026-08-28")
        self.assertTrue(any("predates the current redaction contract" in n for n in notes))


if __name__ == "__main__":
    unittest.main()
