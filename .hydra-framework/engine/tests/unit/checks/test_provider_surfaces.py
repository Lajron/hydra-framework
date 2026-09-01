"""Mirror test for `hydra_engine.checks.provider_surfaces`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import provider_surfaces  # noqa: E402


class ProviderSurfaceFindingsTests(unittest.TestCase):
    def test_generated_surfaces_are_not_findings(self) -> None:
        surfaces = [{"path": ".claude/skills/x/SKILL.md", "status": "generated", "detail": ""}]
        self.assertEqual(provider_surfaces.provider_surface_findings(surfaces), [])

    def test_unmanaged_surfaces_reproduce_the_original_message(self) -> None:
        surfaces = [{"path": ".claude/skills/x/SKILL.md", "status": "orphaned", "detail": "no canonical source"}]
        findings = provider_surfaces.provider_surface_findings(surfaces)
        self.assertEqual(len(findings), 1)
        self.assertEqual(str(findings[0]), ".claude/skills/x/SKILL.md: orphaned provider surface: no canonical source")
        self.assertEqual(findings[0].path, ".claude/skills/x/SKILL.md")

    def test_only_non_generated_surfaces_are_kept(self) -> None:
        surfaces = [
            {"path": "a", "status": "generated", "detail": ""},
            {"path": "b", "status": "orphaned", "detail": "d"},
        ]
        findings = provider_surfaces.provider_surface_findings(surfaces)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].path, "b")


if __name__ == "__main__":
    unittest.main()
