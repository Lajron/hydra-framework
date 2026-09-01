"""Move classification.

Unambiguous manual moves may be repaired and ambiguous ones must be reported
for a human or agent to decide, never guessed. The mechanical definition of
"unambiguous" is `classify_object_move` below:
a total function over three recorded fields and three current fields, with no
heuristics, no similarity scoring, and no tie-breaking.

`path_exists_from_registry` lives here rather than in `registry.py` because
`detect_object_moves` is its original and primary caller; `registry.py`
imports it from here instead, which is the only direction that keeps the two
modules acyclic (`registry.py` already needs `detect_object_moves`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hydra_engine.documents.yaml_documents import yaml_str

UNAMBIGUOUS_MOVE = "unambiguous-move"
AMBIGUOUS_MOVE = "ambiguous-move"
NOT_A_MOVE = "not-a-move"

MOVE_REASONS = {
    "same-path": "the recorded path is still the current path",
    "unknown-identity": "no uid on one or both sides, so identity cannot be proven",
    "different-uid": "the uid differs, so these are different objects",
    "content-changed": "the digest changed, so this is an edit as well as a relocation",
    "recorded-path-still-present": "a file still sits at the recorded path, so this reads as a copy",
    "no-candidate": "nothing in the tree carries this object's identity",
    "multiple-candidates": "more than one current object carries this uid",
    "moved": "same uid, same digest, new path",
}


@dataclass(frozen=True)
class MoveVerdict:
    classification: str
    reason: str

    @property
    def is_unambiguous(self) -> bool:
        return self.classification == UNAMBIGUOUS_MOVE

    def detail(self) -> str:
        return MOVE_REASONS.get(self.reason, self.reason)


@dataclass(frozen=True)
class ObjectMove:
    """One registry entry compared against whatever now carries its identity."""

    recorded_id: str
    current_id: str
    uid: str
    from_path: str
    to_path: str
    verdict: MoveVerdict


def classify_object_move(
    *,
    recorded_uid: str,
    recorded_path: str,
    recorded_digest: str,
    current_uid: str,
    current_path: str,
    current_digest: str,
    recorded_path_occupied: bool,
) -> MoveVerdict:
    """The mechanical test for an unambiguous move.

    Same uid, same digest, different path, and nothing left behind at the old
    path is the only combination that is a move an agent may repair on its
    own. Every other combination is either not a move at all or is ambiguous
    and must be reported rather than guessed:

    - uid missing on either side: identity is unproven, so a matching digest
      alone could equally be an unrelated file with identical content.
    - uid differs: two distinct objects, whatever their paths and content.
    - digest changed: the object was edited as well as relocated, so a
      relocation cannot be told apart from a delete plus an unrelated write.
    - a file still sits at the recorded path: this reads as a copy, and which
      of the two files is the object is not mechanically decidable.
    """
    if recorded_path == current_path:
        return MoveVerdict(NOT_A_MOVE, "same-path")
    if not recorded_uid or not current_uid:
        return MoveVerdict(AMBIGUOUS_MOVE, "unknown-identity")
    if recorded_uid != current_uid:
        return MoveVerdict(NOT_A_MOVE, "different-uid")
    if recorded_digest != current_digest:
        return MoveVerdict(AMBIGUOUS_MOVE, "content-changed")
    if recorded_path_occupied:
        return MoveVerdict(AMBIGUOUS_MOVE, "recorded-path-still-present")
    return MoveVerdict(UNAMBIGUOUS_MOVE, "moved")


def path_exists_from_registry(value: str, paths: ObjectLocations) -> bool:
    if not value:
        return False
    if value.startswith((".hydra-framework/", ".hydra-framework.local/", "project-wiki/")):
        return (paths.root / value).exists()
    path = Path(value)
    return path.exists() if path.is_absolute() else (paths.root / path).exists()


def detect_object_moves(
    registry: dict[str, dict[str, object]],
    objects: list[dict],
    paths: ObjectLocations,
) -> list[ObjectMove]:
    """Compare every registry entry against the current tree.

    Pairing uses the readable `hydra_id` when it still exists, and falls back
    to the opaque `uid` when it does not - that fallback is the whole reason
    the object model keeps a second identity: a readable ID that is itself
    renamed would otherwise be indistinguishable from a delete plus an add.
    """
    current_by_id = {obj["id"]: obj for obj in objects}
    # Built once, outside the loop below: `registry` and `objects` do not
    # change while this function runs, so indexing the unregistered objects
    # by uid/digest a single time turns what used to be a linear rescan per
    # missing registry entry (O(n^2) over the tree) into O(1) lookups.
    unregistered = [obj for obj in objects if obj["id"] not in registry]
    unregistered_by_uid: dict[str, list[dict]] = {}
    unregistered_by_digest: dict[str, list[dict]] = {}
    for obj in unregistered:
        if obj["uid"]:
            unregistered_by_uid.setdefault(obj["uid"], []).append(obj)
        unregistered_by_digest.setdefault(obj["digest"], []).append(obj)

    moves: list[ObjectMove] = []
    for hydra_id, entry in sorted(registry.items()):
        recorded_path = yaml_str(entry.get("path"))
        recorded_digest = yaml_str(entry.get("digest"))
        recorded_uid = yaml_str(entry.get("uid"))
        occupied = path_exists_from_registry(recorded_path, paths)

        current = current_by_id.get(hydra_id)
        if current is None:
            if recorded_uid:
                candidates = unregistered_by_uid.get(recorded_uid, [])
            else:
                # Without a recorded uid the digest is the only signal left,
                # and it is never enough on its own to authorize a repair.
                candidates = unregistered_by_digest.get(recorded_digest, [])
            if not candidates:
                moves.append(
                    ObjectMove(hydra_id, "", recorded_uid, recorded_path, "", MoveVerdict(NOT_A_MOVE, "no-candidate"))
                )
                continue
            if len(candidates) > 1:
                moves.append(
                    ObjectMove(
                        hydra_id,
                        ", ".join(sorted(obj["id"] for obj in candidates)),
                        recorded_uid,
                        recorded_path,
                        ", ".join(sorted(obj["path"] for obj in candidates)),
                        MoveVerdict(AMBIGUOUS_MOVE, "multiple-candidates"),
                    )
                )
                continue
            current = candidates[0]

        verdict = classify_object_move(
            recorded_uid=recorded_uid,
            recorded_path=recorded_path,
            recorded_digest=recorded_digest,
            current_uid=current["uid"],
            current_path=current["path"],
            current_digest=current["digest"],
            recorded_path_occupied=occupied,
        )
        if verdict.classification == NOT_A_MOVE and verdict.reason == "same-path":
            continue
        moves.append(
            ObjectMove(hydra_id, current["id"], recorded_uid, recorded_path, current["path"], verdict)
        )
    return moves
