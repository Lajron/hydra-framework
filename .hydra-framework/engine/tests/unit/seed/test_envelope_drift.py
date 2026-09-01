"""Mirror test for `hydra_engine.seed.envelope_drift`.

Split from `test_hydra.py`'s `DiffBaseSchemaDriftTests`, which drove the
whole `command_diff_base` command end-to-end while monkeypatching
`hydra.HYDRA`/`hydra.LOCAL`/`hydra.OBJECT_REGISTRY`/`hydra.ROOT`; converted
to calling `envelope_schema_drift` directly against two hermetic
`ObjectLocations` trees, since the move itself is what makes that isolation
possible.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity.schema_versions import CURRENT_SCHEMA_VERSION  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402
from hydra_engine.seed.envelope_drift import envelope_schema_drift  # noqa: E402

UNIT_TEMPLATE = (
    "---\n"
    "hydra_id: hydra://knowledge-unit/0001-test\n"
    "kind: knowledge-unit\n"
    "title: Test Object\n"
    "status: active\n"
    "scope: base-seed\n"
    "{schema_line}"
    "relations:\n"
    "provenance:\n"
    "  sources: []\n"
    "---\n"
    "# Test Object\n"
)


def _seed_unit(hydra_root: Path, schema_version: int | None) -> None:
    path = hydra_root / "repo/knowledge-units/0001-test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    schema_line = f"schema_version: {schema_version}\n" if schema_version is not None else ""
    path.write_text(UNIT_TEMPLATE.format(schema_line=schema_line), encoding="utf-8")


def _local_paths() -> ObjectLocations:
    root = Path(tempfile.mkdtemp(prefix="envelope-drift-local-"))
    hydra = root / ".hydra-framework"
    return ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )


class EnvelopeSchemaDriftTests(unittest.TestCase):
    def test_local_behind_on_schema_version_is_classified_as_explained(self):
        local_paths = _local_paths()
        base_hydra = Path(tempfile.mkdtemp(prefix="envelope-drift-base-")) / ".hydra-framework"
        _seed_unit(local_paths.hydra, schema_version=None)
        _seed_unit(base_hydra, schema_version=CURRENT_SCHEMA_VERSION + 1)

        drift = envelope_schema_drift(local_paths, base_hydra)

        self.assertIn("repo/knowledge-units/0001-test.md", drift)
        reason = drift["repo/knowledge-units/0001-test.md"]
        self.assertIn("schema_version", reason)
        self.assertIn("hydra.py schema upgrade", reason)

    def test_matching_schema_versions_have_no_drift(self):
        local_paths = _local_paths()
        base_hydra = Path(tempfile.mkdtemp(prefix="envelope-drift-base-")) / ".hydra-framework"
        _seed_unit(local_paths.hydra, schema_version=CURRENT_SCHEMA_VERSION)
        _seed_unit(base_hydra, schema_version=CURRENT_SCHEMA_VERSION)

        self.assertEqual(envelope_schema_drift(local_paths, base_hydra), {})

    def test_local_ahead_of_base_is_not_drift(self):
        local_paths = _local_paths()
        base_hydra = Path(tempfile.mkdtemp(prefix="envelope-drift-base-")) / ".hydra-framework"
        _seed_unit(local_paths.hydra, schema_version=CURRENT_SCHEMA_VERSION)
        _seed_unit(base_hydra, schema_version=CURRENT_SCHEMA_VERSION - 1 if CURRENT_SCHEMA_VERSION > 0 else 0)

        self.assertEqual(envelope_schema_drift(local_paths, base_hydra), {})

    def test_malformed_local_object_yields_no_drift_rather_than_raising(self):
        local_paths = _local_paths()
        local_paths.hydra.mkdir(parents=True)
        bad = local_paths.hydra / "repo/knowledge-units/0001-test.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("---\nhydra_id: not-a-valid-id\n---\n# Broken\n", encoding="utf-8")
        base_hydra = Path(tempfile.mkdtemp(prefix="envelope-drift-base-")) / ".hydra-framework"
        _seed_unit(base_hydra, schema_version=CURRENT_SCHEMA_VERSION)

        self.assertEqual(envelope_schema_drift(local_paths, base_hydra), {})


if __name__ == "__main__":
    unittest.main()
