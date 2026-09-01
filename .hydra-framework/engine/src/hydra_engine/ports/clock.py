"""Clock port.

The sole source of "now" for the engine. Callers reach `today()` and
`now_utc_iso()` as module functions (not bound aliases) so a golden fixture
can patch `hydra_engine.ports.clock.today`/`now_utc_iso` directly and every
caller picks up the frozen value without its own patch target.
"""

from __future__ import annotations

import datetime as _dt


def today() -> str:
    return _dt.date.today().isoformat()


def now_utc_iso() -> str:
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def now_local_iso_seconds() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def filename_stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
