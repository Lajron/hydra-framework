"""Host-repository integration logic.

Host-stack detection, the adoption report/lineage recording, what travels
when this Hydra copy is seeded into a target repository, and pointing Git at
the tracked hooks directory -- for `adopt`, `init`, and `install-hooks`.
`PROVIDERS` (the provider registry) is reused from `providers.capabilities`
rather than duplicated again.
"""

from __future__ import annotations
