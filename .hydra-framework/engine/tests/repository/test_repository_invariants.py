"""Repository invariants. Moved from
`scripts/tests/test_hydra.py`'s frozen `RepositoryInvariantTests`, one of the
named Hard-Constraint live-repository classes. Each check runs
against this repository's own real state, calling `hydra_engine.*` directly
instead of a `hydra.py` delegator now that none exist any more.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import module_metadata as module_metadata_engine  # noqa: E402
from hydra_engine.checks.task_contract_docs import REQUIRED_TASK_SECTIONS, validate_task_contract_docs  # noqa: E402
from hydra_engine.documents import yaml_documents as yaml_documents_engine  # noqa: E402
from hydra_engine.installation.adopt import REQUIRED_PATHS  # noqa: E402
from hydra_engine.knowledge.flat_files import validate_flat_knowledge_files  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402
from hydra_engine.work.tiers import validate_private_tier_documented  # noqa: E402
from hydra_engine.wiki.links import validate_root_relative_markdown_links  # noqa: E402
from hydra_engine.providers.capabilities import validate_capability_maps  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402
from hydra_engine.seed.adaptations import validate_adaptations_ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
HYDRA = ROOT / ".hydra-framework"
ADAPTATION_LEDGER = HYDRA / "evolution/adaptations.md"


def _module_metadata_entries() -> list[module_metadata_engine.ModuleMetadataEntry]:
    # Duplicates `scripts/hydra.py`'s own copy of this glob+parse loop: a test
    # file, like the shim, sits outside `documents.yaml_documents`'s
    # architecture-check-4 in-degree count (currently at its cap of 10), so
    # each keeps an independent copy rather than one importing the other.
    entries: list[module_metadata_engine.ModuleMetadataEntry] = []
    for subdir, body_name, required in module_metadata_engine.MODULE_METADATA_CHECKS:
        subdir_root = HYDRA / subdir
        if not subdir_root.is_dir():
            continue
        for module_dir in sorted(p for p in subdir_root.glob("*") if p.is_dir() and (p / body_name).exists()):
            metadata = module_dir / "metadata.yaml"
            data = parse_error = None
            if metadata.exists():
                try:
                    data = yaml_documents_engine.parse_yaml(metadata, ROOT)
                except yaml_documents_engine.HydraYamlError as error:
                    parse_error = str(error)
            entries.append(module_metadata_engine.ModuleMetadataEntry(
                module_dir=module_dir, metadata_path=metadata, required=required,
                is_skill=subdir == "capabilities/skills", data=data, parse_error=parse_error,
            ))
    return entries


class RepositoryInvariantTests(unittest.TestCase):
    def test_module_metadata_is_valid(self) -> None:
        self.assertEqual(module_metadata_engine.validate_module_metadata(_module_metadata_entries(), ROOT), [])

    def test_capability_maps_cover_every_class_and_budget(self) -> None:
        self.assertEqual(validate_capability_maps(ProvidersPaths(root=ROOT, hydra=HYDRA)), [])

    def test_task_contract_docs_agree_with_the_validator(self) -> None:
        self.assertEqual(validate_task_contract_docs(HYDRA, ROOT, REQUIRED_TASK_SECTIONS), [])

    def test_adaptation_ledger_is_valid(self) -> None:
        self.assertEqual(validate_adaptations_ledger(ADAPTATION_LEDGER, ROOT), [])

    def test_checked_in_settings_json_is_valid(self) -> None:
        settings = ROOT / ".claude/settings.json"
        if not settings.exists():
            self.skipTest("no .claude/settings.json in this repository")
        data = json.loads(settings.read_text(encoding="utf-8"))
        self.assertIn("hooks", data)

    def test_required_paths_exist(self) -> None:
        missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
        self.assertEqual(missing, [])

    def test_private_tier_seed_is_documented(self) -> None:
        paths = WorkPaths(root=ROOT, hydra=HYDRA, local=ROOT / ".hydra-framework.local")
        self.assertEqual(validate_private_tier_documented(paths), [])

    def test_project_wiki_markdown_links_are_root_relative(self) -> None:
        self.assertEqual(validate_root_relative_markdown_links(ROOT / "project-wiki", ROOT), [])

    def test_flat_knowledge_files_have_minimum_envelopes(self) -> None:
        self.assertEqual(validate_flat_knowledge_files(HYDRA, ROOT), [])

    def test_no_example_tree_references(self) -> None:
        needle = ".hydra-framework" ".local" ".example"
        result = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True)
        offenders = []
        for rel in result.stdout.splitlines():
            if rel.startswith(".migrations/"):
                continue
            path = ROOT / rel
            if path.is_file() and needle in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(rel)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
