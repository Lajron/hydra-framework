"""Mirror test for `hydra_engine.seed.candidate_queue`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.seed import candidate_queue  # noqa: E402


def _dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="seed-candidate-queue-"))


def _write_candidate(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def _candidate_text(*, status: str = "proposed", author: str = "dana", created: str = "2026-08-01") -> str:
    return "\n".join([
        "# Improvement: example",
        "",
        f"Status: {status}",
        f"Author: {author}",
        f"Created: {created}",
        "",
        "## Change",
        "",
        "Do the thing.",
        "",
    ])


class ParseCandidateHeaderTests(unittest.TestCase):
    def test_parses_header_fields(self):
        fields = candidate_queue.parse_candidate_header(_candidate_text())
        self.assertEqual(fields["Status"], "proposed")
        self.assertEqual(fields["Author"], "dana")
        self.assertEqual(fields["Created"], "2026-08-01")

    def test_field_shaped_prose_in_a_section_is_not_mistaken_for_a_header_field(self):
        text = _candidate_text().replace("Do the thing.", "Status: this looks like a field but is not")
        fields = candidate_queue.parse_candidate_header(text)
        self.assertEqual(fields["Status"], "proposed")


class ValidateCandidateFileTests(unittest.TestCase):
    def test_valid_candidate_passes(self):
        fields = candidate_queue.parse_candidate_header(_candidate_text())
        findings = candidate_queue.validate_candidate_file(fields, "evolution/candidates/2026-08-01-example.md")
        self.assertEqual(findings, [])

    def test_all_terminal_statuses_pass(self):
        for status in ("accepted", "rejected", "captured", "superseded"):
            fields = candidate_queue.parse_candidate_header(_candidate_text(status=status))
            findings = candidate_queue.validate_candidate_file(fields, "evolution/candidates/2026-08-01-example.md")
            self.assertEqual(findings, [], f"status {status} should pass")

    def test_missing_author_fails(self):
        text = _candidate_text().replace("Author: dana\n", "")
        fields = candidate_queue.parse_candidate_header(text)
        findings = candidate_queue.validate_candidate_file(fields, "evolution/candidates/2026-08-01-example.md")
        self.assertTrue(any("Author" in f.detail for f in findings))

    def test_unknown_status_fails(self):
        fields = candidate_queue.parse_candidate_header(_candidate_text(status="in-review"))
        findings = candidate_queue.validate_candidate_file(fields, "evolution/candidates/2026-08-01-example.md")
        self.assertTrue(any("Status" in f.detail for f in findings))

    def test_invalid_created_date_fails(self):
        fields = candidate_queue.parse_candidate_header(_candidate_text(created="not-a-date"))
        findings = candidate_queue.validate_candidate_file(fields, "evolution/candidates/2026-08-01-example.md")
        self.assertTrue(any("Created" in f.detail for f in findings))


class ValidateCandidateQueueTests(unittest.TestCase):
    def test_absent_directory_is_valid(self):
        directory = _dir() / "candidates"
        self.assertEqual(candidate_queue.validate_candidate_queue(directory, directory.parent), [])

    def test_readme_is_never_validated_as_a_candidate(self):
        directory = _dir()
        _write_candidate(directory, "README.md", "# Evolution Candidates\n")
        self.assertEqual(candidate_queue.validate_candidate_queue(directory, directory.parent), [])

    def test_valid_candidate_in_a_real_directory_passes(self):
        directory = _dir()
        _write_candidate(directory, "2026-08-01-example.md", _candidate_text())
        self.assertEqual(candidate_queue.validate_candidate_queue(directory, directory.parent), [])

    def test_split_candidate_subdirectory_is_not_scanned(self):
        directory = _dir()
        _write_candidate(directory, "2026-08-01-example.md", _candidate_text())
        part_dir = directory / "2026-08-01-example"
        part_dir.mkdir()
        _write_candidate(part_dir, "part-one.md", "# Part One\n\nno header here\n")
        self.assertEqual(candidate_queue.validate_candidate_queue(directory, directory.parent), [])

    def test_broken_candidate_is_reported(self):
        directory = _dir()
        _write_candidate(directory, "2026-08-01-example.md", _candidate_text(status="in-review"))
        findings = candidate_queue.validate_candidate_queue(directory, directory.parent)
        self.assertEqual(len(findings), 1)


class CandidateQueueNotesTests(unittest.TestCase):
    def test_absent_directory_is_silent(self):
        directory = _dir() / "candidates"
        self.assertEqual(candidate_queue.candidate_queue_notes(directory, directory.parent, "2026-08-24"), [])

    def test_fresh_proposed_candidate_is_silent(self):
        directory = _dir()
        _write_candidate(directory, "2026-08-20-example.md", _candidate_text(created="2026-08-20"))
        self.assertEqual(candidate_queue.candidate_queue_notes(directory, directory.parent, "2026-08-24"), [])

    def test_configured_staleness_days_affects_notes(self):
        directory = _dir()
        _write_candidate(directory, "2026-08-20-example.md", _candidate_text(created="2026-08-20"))
        notes = candidate_queue.candidate_queue_notes(directory, directory.parent, "2026-08-24", stale_days=2)
        self.assertTrue(any("2-day decision expectation" in note for note in notes))

    def test_stale_proposed_candidate_produces_a_note(self):
        directory = _dir()
        _write_candidate(directory, "2026-01-01-example.md", _candidate_text(created="2026-01-01"))
        notes = candidate_queue.candidate_queue_notes(directory, directory.parent, "2026-08-24")
        self.assertTrue(any("2026-01-01-example.md" in note for note in notes))

    def test_terminal_status_is_never_flagged_regardless_of_age(self):
        directory = _dir()
        _write_candidate(directory, "2026-01-01-example.md", _candidate_text(status="accepted", created="2026-01-01"))
        self.assertEqual(candidate_queue.candidate_queue_notes(directory, directory.parent, "2026-08-24"), [])


if __name__ == "__main__":
    unittest.main()
