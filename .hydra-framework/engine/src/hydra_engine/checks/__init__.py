"""Layer-3 checks: validators that aggregate across layer 2.

`module_metadata.py`/`task_contract_docs.py` hold the two repo-wide
validators that were never delegators before (no domain cluster
owned them); `provider_surfaces.py`/`architecture_check.py` wrap
not-`validate_*`-named or intentionally-import-free producers
(`providers.reclaim.classify_surfaces`, `architecture.check()`) into
`Finding`; `aggregation.py` runs a precomputed list of such checks without
importing any of them itself.
"""

from __future__ import annotations
