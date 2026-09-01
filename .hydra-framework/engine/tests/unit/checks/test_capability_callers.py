"""Mirror test for `hydra_engine.checks.capability_callers`."""

from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import capability_callers  # noqa: E402


def _root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="capability-callers-test-"))
    (root / ".hydra-framework/scripts").mkdir(parents=True)
    (root / ".hydra-framework/engine/src/hydra_engine/commands").mkdir(parents=True)
    (root / ".hydra-framework/validation").mkdir(parents=True)
    return root


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def _write_empty_evidence(root: Path) -> None:
    evidence = root / ".hydra-framework/validation/capability-callers.yaml"
    _write(
        evidence,
        """
        schema: hydra-framework.capability-callers.v1
        mechanisms:
          fixture:
            classification: manual
            implementation:
              .hydra-framework/validation/capability-callers.yaml:
                - fixture
            callers:
              .hydra-framework/validation/capability-callers.yaml:
                - manual
        """,
    )


class CommandArgparseCoverageTests(unittest.TestCase):
    def test_registered_dispatch_wrapper_covers_command_implementation(self) -> None:
        root = _root()
        _write_empty_evidence(root)
        _write(
            root / ".hydra-framework/engine/src/hydra_engine/commands/sample.py",
            """
            def command_sample(args):
                return 0

            def _dispatch_sample(args, ctx):
                return command_sample(args)

            def register(subparsers):
                parser = subparsers.add_parser("sample")
                parser.set_defaults(func=_dispatch_sample)
            """,
        )
        findings = capability_callers.validate_capability_callers(root / ".hydra-framework", root)
        self.assertEqual(findings, [])

    def test_registered_lambda_covers_command_implementation(self) -> None:
        root = _root()
        _write_empty_evidence(root)
        _write(
            root / ".hydra-framework/scripts/hydra.py",
            """
            def command_selftest(args):
                return 0

            def register(subparsers):
                parser = subparsers.add_parser("selftest")
                parser.set_defaults(func=lambda args, ctx: command_selftest(args))
            """,
        )
        findings = capability_callers.validate_capability_callers(root / ".hydra-framework", root)
        self.assertEqual(findings, [])

    def test_unregistered_command_reports_finding(self) -> None:
        root = _root()
        _write_empty_evidence(root)
        _write(
            root / ".hydra-framework/engine/src/hydra_engine/commands/sample.py",
            """
            def command_sample(args):
                return 0
            """,
        )
        findings = capability_callers.validate_capability_callers(root / ".hydra-framework", root)
        self.assertEqual(len(findings), 1)
        self.assertIn("defines `command_sample` with no argparse caller", findings[0])


class EvidenceFileTests(unittest.TestCase):
    def test_validates_classification_and_snippets(self) -> None:
        root = _root()
        _write(
            root / "docs.md",
            """
            Manual caller: hydra.py sample
            Implementation: def command_sample
            """,
        )
        _write(
            root / ".hydra-framework/validation/capability-callers.yaml",
            """
            schema: hydra-framework.capability-callers.v1
            mechanisms:
              sample:
                classification: manual
                implementation:
                  docs.md:
                    - def command_sample
                callers:
                  docs.md:
                    - Manual caller
            """,
        )
        findings = capability_callers.validate_capability_callers(root / ".hydra-framework", root)
        self.assertEqual(findings, [])

    def test_invalid_classification_reports_finding(self) -> None:
        root = _root()
        _write(
            root / "docs.md",
            """
            Manual caller
            def command_sample
            """,
        )
        _write(
            root / ".hydra-framework/validation/capability-callers.yaml",
            """
            schema: hydra-framework.capability-callers.v1
            mechanisms:
              sample:
                classification: maybe
                implementation:
                  docs.md:
                    - def command_sample
                callers:
                  docs.md:
                    - Manual caller
            """,
        )
        findings = capability_callers.validate_capability_callers(root / ".hydra-framework", root)
        self.assertTrue(any("classification must be one of" in finding for finding in findings))

    def test_missing_snippet_reports_finding(self) -> None:
        root = _root()
        _write(root / "docs.md", "Manual caller\n")
        _write(
            root / ".hydra-framework/validation/capability-callers.yaml",
            """
            schema: hydra-framework.capability-callers.v1
            mechanisms:
              sample:
                classification: manual
                implementation:
                  docs.md:
                    - def command_sample
                callers:
                  docs.md:
                    - Manual caller
            """,
        )
        findings = capability_callers.validate_capability_callers(root / ".hydra-framework", root)
        self.assertTrue(any("does not contain `def command_sample`" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
