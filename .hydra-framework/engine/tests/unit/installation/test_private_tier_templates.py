"""Mirror test for `hydra_engine.installation.private_tier_templates`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.installation.private_tier import PRIVATE_TIER_SEED  # noqa: E402
from hydra_engine.installation.private_tier_templates import (  # noqa: E402
    AREA_README,
    DEVELOPER_PREFERENCES_STUB,
    MACHINE_PROFILE_STUB,
    MIGRATION_STAGING_README,
    SECRETS_README,
    TOKEN_USAGE_TEMPLATE,
    TOP_LEVEL_README,
)


class PrivateTierTemplateTests(unittest.TestCase):
    def test_every_seed_area_has_a_readme(self) -> None:
        self.assertEqual([area.path for area in PRIVATE_TIER_SEED if area.path not in AREA_README], [])

    def test_no_template_is_empty(self) -> None:
        templates = [
            TOP_LEVEL_README,
            TOKEN_USAGE_TEMPLATE,
            MIGRATION_STAGING_README,
            DEVELOPER_PREFERENCES_STUB,
            MACHINE_PROFILE_STUB,
            SECRETS_README,
            *AREA_README.values(),
        ]
        self.assertTrue(all(template.strip() for template in templates))


if __name__ == "__main__":
    unittest.main()
