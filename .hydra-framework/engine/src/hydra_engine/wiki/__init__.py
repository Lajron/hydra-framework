"""Human wiki surface logic.

Markdown/Obsidian link validation and `project-wiki/<slug>` scaffold
generation for `validate-wiki` and `wiki scaffold`. `validate_markdown_links`
is reused by `knowledge.package_checks.validate_package_root` against
knowledge-package directories, not just the wiki -- `scripts/hydra.py` keeps
a same-name thin delegator to `links.py` so that caller needs no change.
"""

from __future__ import annotations
