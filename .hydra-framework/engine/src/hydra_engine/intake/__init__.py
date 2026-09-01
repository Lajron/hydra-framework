"""Migration staging inventory and ledger logic.

Classifies already-shared material staged under `.migrations/<slug>/` and
scaffolds the shared `intake/migrations/<date>-<slug>/` triage workspace for
`migration inventory` and `migration ledger`. Read-only inventory; a ledger
records triage decisions, it never moves or promotes staged files itself.
"""

from __future__ import annotations
