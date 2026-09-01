"""Mirror test for `hydra_engine.ports.clock`."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.ports import clock  # noqa: E402

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UTC_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_LOCAL_ISO_SECONDS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
_FILENAME_STAMP_RE = re.compile(r"^\d{8}-\d{6}$")


class ClockTests(unittest.TestCase):
    def test_today_is_an_iso_date(self):
        self.assertRegex(clock.today(), _DATE_RE)

    def test_now_utc_iso_is_zulu_with_no_microseconds(self):
        self.assertRegex(clock.now_utc_iso(), _UTC_ISO_RE)

    def test_now_local_iso_seconds_has_no_microseconds_or_timezone(self):
        self.assertRegex(clock.now_local_iso_seconds(), _LOCAL_ISO_SECONDS_RE)

    def test_filename_stamp_is_sortable_and_filesystem_safe(self):
        self.assertRegex(clock.filename_stamp(), _FILENAME_STAMP_RE)


if __name__ == "__main__":
    unittest.main()
