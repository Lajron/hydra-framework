"""Mirror test for `hydra_engine.work.owners`.

`OwnerResolutionTests` moved from `scripts/tests/test_hydra.py`: this version
calls `resolve_owner` directly with explicit arguments instead of
monkeypatching `hydra.os.environ`/`hydra.git_config_email`, since the move
itself is what makes that isolation possible for the first time.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.work import owners  # noqa: E402


class ResolveOwnerTests(unittest.TestCase):
    def test_explicit_owner_wins(self) -> None:
        self.assertEqual(owners.resolve_owner("Explicit Person", "from-env", "git@example.com"), "explicit-person")

    def test_env_overrides_git_config(self) -> None:
        self.assertEqual(owners.resolve_owner("", "service-account", "git@example.com"), "service-account")

    def test_email_is_slugified_in_full_domain_included(self) -> None:
        self.assertEqual(owners.resolve_owner("", "", "Dana.Reed@Example.COM"), "dana-reed-example-com")

    def test_unset_identity_raises_instead_of_defaulting(self) -> None:
        with self.assertRaises(owners.HydraOwnerError) as caught:
            owners.resolve_owner("", "", "")
        # The error has to say how to fix it; a bare raise just moves the guess
        # to whoever reads the traceback.
        self.assertIn("git config user.email", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
