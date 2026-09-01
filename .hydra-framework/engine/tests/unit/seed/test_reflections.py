"""Mirror test for `hydra_engine.seed.reflections`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.seed import reflections  # noqa: E402


def _dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="seed-reflections-"))


def _write_packet(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def _packet_text(*, status: str = "open", held_until: str = "", created: str = "2026-08-01", extra_evidence_lines: int = 1) -> str:
    lines = [
        "# 2026-08-01 - Example Observation",
        "",
        f"Status: {status}",
        "Author: dana",
        f"Created: {created}",
        "Updated: 2026-08-01",
        "Scope: example",
    ]
    if held_until:
        lines.append(f"Held-Until: {held_until}")
    lines += [
        "",
        "## Observation",
        "",
        "Something durable happened.",
        "",
        "## Evidence",
        "",
    ]
    lines += [f"- evidence line {i}" for i in range(extra_evidence_lines)]
    lines += [
        "",
        "## Suggested Outcome",
        "",
        "Maybe promote it.",
        "",
    ]
    return "\n".join(lines)


class ParseReflectionPacketTextTests(unittest.TestCase):
    def test_parses_header_fields_and_sections(self):
        entry = reflections.parse_reflection_packet_text(_packet_text())
        self.assertEqual(entry["fields"]["Status"], "open")
        self.assertEqual(entry["fields"]["Author"], "dana")
        self.assertEqual(entry["sections"], set(reflections.REQUIRED_SECTIONS))

    def test_field_shaped_prose_in_a_section_is_not_mistaken_for_a_header_field(self):
        text = _packet_text().replace("- evidence line 0", "- Status: this looks like a field but is not")
        entry = reflections.parse_reflection_packet_text(text)
        self.assertEqual(entry["fields"]["Status"], "open")


class ValidateReflectionPacketTests(unittest.TestCase):
    def test_valid_open_packet_passes(self):
        entry = reflections.parse_reflection_packet_text(_packet_text())
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertEqual(findings, [])

    def test_valid_held_packet_passes(self):
        entry = reflections.parse_reflection_packet_text(_packet_text(status="held", held_until="2026-09-01"))
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertEqual(findings, [])

    def test_bad_filename_fails(self):
        entry = reflections.parse_reflection_packet_text(_packet_text())
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/not-a-dated-slug.md")
        self.assertTrue(any("filename" in f.detail for f in findings))

    def test_missing_required_field_fails(self):
        text = _packet_text().replace("Scope: example\n", "")
        entry = reflections.parse_reflection_packet_text(text)
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertTrue(any("Scope" in f.detail for f in findings))

    def test_unknown_status_fails(self):
        entry = reflections.parse_reflection_packet_text(_packet_text(status="in-review"))
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertTrue(any("Status" in f.detail for f in findings))

    def test_held_without_held_until_fails(self):
        entry = reflections.parse_reflection_packet_text(_packet_text(status="held"))
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertTrue(any("Held-Until" in f.detail for f in findings))

    def test_held_with_invalid_held_until_fails(self):
        entry = reflections.parse_reflection_packet_text(_packet_text(status="held", held_until="not-a-date"))
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertTrue(any("Held-Until" in f.detail for f in findings))

    def test_open_with_held_until_fails(self):
        entry = reflections.parse_reflection_packet_text(_packet_text(status="open", held_until="2026-09-01"))
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertTrue(any("must not carry" in f.detail for f in findings))

    def test_missing_section_fails(self):
        text = _packet_text().replace("## Evidence", "## Not Evidence")
        entry = reflections.parse_reflection_packet_text(text)
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertTrue(any("## Evidence" in f.detail for f in findings))

    def test_oversized_packet_fails(self):
        entry = reflections.parse_reflection_packet_text(_packet_text(extra_evidence_lines=2000))
        findings = reflections.validate_reflection_packet(entry, "evolution/reflections/2026-08-01-example.md")
        self.assertTrue(any("token" in f.detail for f in findings))

    def test_configured_packet_ceiling_affects_validation(self):
        entry = reflections.parse_reflection_packet_text(_packet_text())
        findings = reflections.validate_reflection_packet(
            entry, "evolution/reflections/2026-08-01-example.md", fail_tokens=1,
        )
        self.assertTrue(any("1-token ceiling" in f.detail for f in findings))


class ValidateReflectionQueueTests(unittest.TestCase):
    def test_absent_directory_is_valid(self):
        directory = _dir() / "reflections"
        self.assertEqual(reflections.validate_reflection_queue(directory, directory.parent), [])

    def test_readme_is_never_validated_as_a_packet(self):
        directory = _dir()
        _write_packet(directory, "README.md", "# Reflection Queue\n")
        self.assertEqual(reflections.validate_reflection_queue(directory, directory.parent), [])

    def test_valid_packet_in_a_real_directory_passes(self):
        directory = _dir()
        _write_packet(directory, "2026-08-01-example.md", _packet_text())
        self.assertEqual(reflections.validate_reflection_queue(directory, directory.parent), [])

    def test_broken_packet_is_reported_once_per_file(self):
        directory = _dir()
        _write_packet(directory, "2026-08-01-example.md", _packet_text(status="held"))
        findings = reflections.validate_reflection_queue(directory, directory.parent)
        self.assertEqual(len(findings), 1)


class ReflectionQueueNotesTests(unittest.TestCase):
    def test_absent_directory_is_silent(self):
        directory = _dir() / "reflections"
        self.assertEqual(reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24"), [])

    def test_fresh_open_packet_is_silent(self):
        directory = _dir()
        _write_packet(directory, "2026-08-20-example.md", _packet_text(created="2026-08-20"))
        self.assertEqual(reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24"), [])

    def test_configured_staleness_days_affects_notes(self):
        directory = _dir()
        _write_packet(directory, "2026-08-20-example.md", _packet_text(created="2026-08-20"))
        notes = reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24", stale_days=2)
        self.assertTrue(any("2-day drain expectation" in note for note in notes))

    def test_stale_open_packet_produces_a_note(self):
        directory = _dir()
        _write_packet(directory, "2026-01-01-example.md", _packet_text(created="2026-01-01"))
        notes = reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24")
        self.assertTrue(any("2026-01-01-example.md" in note for note in notes))

    def test_held_packet_past_its_date_produces_a_note(self):
        directory = _dir()
        _write_packet(directory, "2026-08-01-example.md", _packet_text(status="held", held_until="2026-08-10"))
        notes = reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24")
        self.assertTrue(any("Held-Until" in note for note in notes))

    def test_held_packet_not_yet_due_is_silent(self):
        directory = _dir()
        _write_packet(directory, "2026-08-01-example.md", _packet_text(status="held", held_until="2026-09-01"))
        self.assertEqual(reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24"), [])

    def test_depth_note_fires_above_the_threshold(self):
        directory = _dir()
        for i in range(reflections.REFLECTION_QUEUE_DEPTH_NOTE + 1):
            _write_packet(directory, f"2026-08-{i + 1:02d}-example.md", _packet_text(created="2026-08-24"))
        notes = reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24")
        self.assertTrue(any("readability backstop" in note for note in notes))

    def test_configured_depth_note_affects_notes(self):
        directory = _dir()
        for i in range(2):
            _write_packet(directory, f"2026-08-{i + 1:02d}-example.md", _packet_text(created="2026-08-24"))
        notes = reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24", depth_note=1)
        self.assertTrue(any("1-packet readability backstop" in note for note in notes))

    def test_depth_note_silent_at_the_threshold(self):
        directory = _dir()
        for i in range(reflections.REFLECTION_QUEUE_DEPTH_NOTE):
            _write_packet(directory, f"2026-08-{i + 1:02d}-example.md", _packet_text(created="2026-08-24"))
        notes = reflections.reflection_queue_notes(directory, directory.parent, "2026-08-24")
        self.assertFalse(any("readability backstop" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
