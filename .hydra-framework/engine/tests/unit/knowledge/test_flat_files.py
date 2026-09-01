"""Unit tests for `hydra_engine.knowledge.flat_files`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import flat_files  # noqa: E402


def _root() -> tuple[Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="flat-knowledge-test-"))
    hydra = root / ".hydra-framework"
    (hydra / "repo/knowledge").mkdir(parents=True)
    return root, hydra


def _write(hydra: Path, name: str, text: str) -> Path:
    path = hydra / "repo/knowledge" / name
    path.write_text(text, encoding="utf-8")
    return path


def _valid(title: str = "Demo") -> str:
    return f"""---
title: {title}
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - AI_SYSTEM.md
---

# {title}
"""


class FlatKnowledgeValidationTests(unittest.TestCase):
    def test_valid_flat_file_has_no_findings(self):
        root, hydra = _root()
        _write(hydra, "demo.md", _valid())
        self.assertEqual(flat_files.validate_flat_knowledge_files(hydra, root), [])

    def test_readme_is_exempt_as_directory_guidance(self):
        root, hydra = _root()
        _write(hydra, "README.md", "# Canonical Repository Knowledge\n")
        self.assertEqual(flat_files.validate_flat_knowledge_files(hydra, root), [])

    def test_missing_frontmatter_is_reported(self):
        root, hydra = _root()
        _write(hydra, "demo.md", "# Demo\n")
        findings = flat_files.validate_flat_knowledge_files(hydra, root)
        self.assertTrue(any("missing flat knowledge frontmatter envelope" in f.detail for f in findings))

    def test_required_fields_are_reported(self):
        root, hydra = _root()
        _write(hydra, "demo.md", "---\ntitle: Demo\n---\n# Demo\n")
        details = "\n".join(f.detail for f in flat_files.validate_flat_knowledge_files(hydra, root))
        self.assertIn("missing `status`", details)
        self.assertIn("missing `owners`", details)
        self.assertIn("missing `certainty` or `updated`/`checked_on` date", details)

    def test_active_file_requires_provenance_sources_key(self):
        root, hydra = _root()
        _write(hydra, "demo.md", """---
title: Demo
status: active
owners:
  team: hydra
certainty: inferred
---
# Demo
""")
        findings = flat_files.validate_flat_knowledge_files(hydra, root)
        self.assertTrue(any("requires `provenance.sources`" in f.detail for f in findings))

    def test_existing_provenance_source_path_is_clean(self):
        root, hydra = _root()
        (root / "docs").mkdir()
        (root / "docs/source.md").write_text("source\n", encoding="utf-8")
        _write(hydra, "demo.md", """---
title: Demo
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - docs/source.md
---
# Demo
""")
        self.assertEqual(flat_files.validate_flat_knowledge_files(hydra, root), [])

    def test_missing_provenance_source_path_is_reported(self):
        root, hydra = _root()
        (root / "docs").mkdir()
        _write(hydra, "demo.md", """---
title: Demo
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - docs/missing.md
---
# Demo
""")
        findings = flat_files.validate_flat_knowledge_files(hydra, root)
        self.assertTrue(any("`provenance.sources` path does not exist: docs/missing.md" in f.detail for f in findings))

    def test_non_path_provenance_source_is_ignored(self):
        root, hydra = _root()
        _write(hydra, "demo.md", """---
title: Demo
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - https://example.invalid/source
---
# Demo
""")
        self.assertEqual(flat_files.validate_flat_knowledge_files(hydra, root), [])

    def test_existing_source_section_path_is_clean(self):
        root, hydra = _root()
        (root / "docs").mkdir()
        (root / "docs/source.md").write_text("source\n", encoding="utf-8")
        _write(hydra, "demo.md", _valid() + "\n## Sources\n\n- `docs/source.md`\n")
        self.assertEqual(flat_files.validate_flat_knowledge_files(hydra, root), [])

    def test_missing_source_section_path_is_reported(self):
        root, hydra = _root()
        (root / "docs").mkdir()
        _write(hydra, "demo.md", _valid() + "\n## Sources\n\n- `docs/missing.md`\n")
        findings = flat_files.validate_flat_knowledge_files(hydra, root)
        self.assertTrue(any("source list path does not exist: docs/missing.md" in f.detail for f in findings))

    def test_non_path_source_section_bullet_is_ignored(self):
        root, hydra = _root()
        _write(hydra, "demo.md", _valid() + "\n## Sources\n\n- Live system review, checked 2026-08-25\n")
        self.assertEqual(flat_files.validate_flat_knowledge_files(hydra, root), [])

    def test_pending_discovery_can_use_updated_without_provenance(self):
        root, hydra = _root()
        _write(hydra, "demo.md", """---
title: Demo
status: pending-discovery
owners:
  team: hydra
updated: 2026-08-25
---
# Demo
""")
        self.assertEqual(flat_files.validate_flat_knowledge_files(hydra, root), [])

    def test_bad_date_is_reported(self):
        root, hydra = _root()
        _write(hydra, "demo.md", """---
title: Demo
status: pending-discovery
owners:
  team: hydra
updated: today
---
# Demo
""")
        findings = flat_files.validate_flat_knowledge_files(hydra, root)
        self.assertTrue(any("YYYY-MM-DD" in f.detail for f in findings))

    def test_duplicate_titles_are_reported(self):
        root, hydra = _root()
        _write(hydra, "a.md", _valid("Same"))
        _write(hydra, "b.md", _valid("Same"))
        findings = flat_files.validate_flat_knowledge_files(hydra, root)
        self.assertTrue(any(f.detail.startswith("duplicate flat knowledge title") for f in findings))

    def test_status_certainty_contradictions_are_reported(self):
        root, hydra = _root()
        _write(hydra, "demo.md", """---
title: Demo
status: active
owners:
  team: hydra
certainty: superseded
provenance:
  sources: []
---
# Demo
""")
        findings = flat_files.validate_flat_knowledge_files(hydra, root)
        self.assertTrue(any("contradicts certainty `superseded`" in f.detail for f in findings))


if __name__ == "__main__":
    unittest.main()
