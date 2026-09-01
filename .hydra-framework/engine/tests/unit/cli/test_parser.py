"""Unit tests for hydra_engine.cli.parser."""

from __future__ import annotations

import unittest

from hydra_engine.cli import parser


class _EchoModule:
    @staticmethod
    def register(subparsers) -> None:
        echo = subparsers.add_parser("echo")
        echo.add_argument("text")
        echo.set_defaults(func=lambda args, ctx: args.text)


class BuildParserTests(unittest.TestCase):
    def test_iterates_every_given_command_module(self) -> None:
        built = parser.build_parser([_EchoModule])
        args = built.parse_args(["echo", "hi"])
        self.assertEqual(args.func(args, None), "hi")

    def test_extra_registers_onto_the_same_subparsers_object(self) -> None:
        seen = []

        def _extra(subparsers):
            legacy = subparsers.add_parser("legacy")
            legacy.set_defaults(func=lambda args, ctx: seen.append("legacy") or 0)

        built = parser.build_parser([_EchoModule], _extra)
        args = built.parse_args(["legacy"])
        args.func(args, None)
        self.assertEqual(seen, ["legacy"])
        # the modules given still register too, alongside `extra`.
        echo_args = built.parse_args(["echo", "hi"])
        self.assertEqual(echo_args.func(echo_args, None), "hi")

    def test_no_command_still_requires_a_subcommand(self) -> None:
        built = parser.build_parser([_EchoModule])
        with self.assertRaises(SystemExit):
            built.parse_args([])


if __name__ == "__main__":
    unittest.main()
