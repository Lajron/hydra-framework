"""source-integration command goldens."""

from __future__ import annotations

import unittest

from .fixtures import assert_golden, hydra_object_markdown, run_golden


SOURCE_FIXTURE = {
    ".migrations/source-a/.hydra-framework/manifest.yaml": (
        "schema: hydra-framework.manifest.v1\n"
        "framework_name: hydra-framework\n"
        "seed_version: 0.1.0\n"
        "lineage:\n"
        "  adopted_into: source-a\n"
    ),
    ".migrations/source-a/.hydra-framework/repo/knowledge-units/0001-source.md": hydra_object_markdown(
        hydra_id="hydra://knowledge-unit/0001-source",
        title="Source Unit",
    ),
}


class IntegrateGoldenTests(unittest.TestCase):
    def test_integrate_scan_happy_path(self):
        outcome = run_golden(["integrate", "scan", "source-a"], extra_fixture=SOURCE_FIXTURE)
        assert_golden(self, "integrate-scan", outcome)

    def test_integrate_map_create_happy_path(self):
        outcome = run_golden(["integrate", "map", "source-a", "--create"], extra_fixture=SOURCE_FIXTURE)
        assert_golden(self, "integrate-map-create", outcome)

    def test_integrate_status_json(self):
        fixture = dict(SOURCE_FIXTURE)
        fixture.update({
            ".hydra-framework/intake/integrations/2026-01-01-source-a/README.md": "# Source\n",
            ".hydra-framework/intake/integrations/2026-01-01-source-a/object-map.yaml": (
                "schema: hydra-framework.source-object-map.v1\n"
                "slug: source-a\n"
                "objects:\n"
                "  - source_id: hydra://source/source-a/knowledge-unit/0001-source\n"
                "    status: pending\n"
            ),
            ".hydra-framework/intake/integrations/2026-01-01-source-a/collisions.yaml": (
                "schema: hydra-framework.source-collisions.v1\n"
                "slug: source-a\n"
                "id_collisions:\n"
                "  - none\n"
                "path_collisions:\n"
                "  - none\n"
                "ambiguous_matches:\n"
                "  - none\n"
            ),
            ".hydra-framework/intake/integrations/2026-01-01-source-a/ledger.md": (
                "| Source Object | Source ID | Verdict | Destination | Status | Notes |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| `hydra://knowledge-unit/0001-source` | `hydra://source/source-a/knowledge-unit/0001-source` | import | TBD | pending | todo |\n"
            ),
        })
        outcome = run_golden(["integrate", "status", "source-a", "--json"], extra_fixture=fixture)
        assert_golden(self, "integrate-status-json", outcome)

    def test_integrate_identify_requires_workspace(self):
        outcome = run_golden(["integrate", "identify", "source-a"], extra_fixture=SOURCE_FIXTURE)
        assert_golden(self, "integrate-identify-no-workspace", outcome)


if __name__ == "__main__":
    unittest.main()
