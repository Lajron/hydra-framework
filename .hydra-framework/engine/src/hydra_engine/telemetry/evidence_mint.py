"""Minting a new telemetry evidence package (see `repo/telemetry/README.md`).

Split from `telemetry.evidence` (validation) once the two together would have
crossed the 400-line architecture ceiling -- this module only ever writes a
package that `evidence.validate_package` already accepts; it holds no
validation logic of its own.

Mechanizes the three mistakes an agent is likeliest to make by hand: a
hand-written `uid`, a directory name that disagrees with its `hydra_id`, and
a hand-copied private row. Judgment stays with whoever fills in `## Question`,
`## Findings`, and `## Method` -- this only ever emits `TODO` for those.
"""

from __future__ import annotations

TODO = "TODO"


def package_dir_name(today: str, owner: str, slug: str) -> str:
    return f"{today}-{owner}-{slug}"


def render_overview(*, dir_name: str, uid: str, owner: str, today: str, title: str) -> str:
    lines = [
        "---",
        f"hydra_id: hydra://telemetry-evidence/{dir_name}",
        f"uid: {uid}",
        "schema_version: 3",
        "kind: telemetry-evidence",
        f"title: {title}",
        "status: open",
        "scope: base-seed",
        "owners:",
        f"  individual: {owner}",
        "relations: []",
        "provenance:",
        "  sources:",
        f"    - .hydra-framework/repo/telemetry/packages/{dir_name}/gate-attestation.json",
        "---",
        "",
        f"# {title}",
        "",
        f"Author: {owner}",
        f"Created: {today}",
        f"Window: {TODO}",
        f"Corpus: {TODO}",
        "",
        "## Question",
        "",
        title,
        "",
        "## Findings",
        "",
        TODO,
        "",
        "## Method",
        "",
        TODO,
        "",
        "## Absorption",
        "",
        TODO,
        "",
    ]
    return "\n".join(lines)
