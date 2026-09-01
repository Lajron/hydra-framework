
# Migration: <short-name>

Type: migration-workspace
Status: active
Created: YYYY-MM-DD
Certainty: unreviewed

## Source Roots

Paths in the host repository this migration is responsible for clearing.

- `<path>/`: <item count>, <size>, <what it appears to be>

## Originals Location

- Private staging: `.hydra-framework.local/migrations/<slug>/originals/`
- Moved on: YYYY-MM-DD
- Git already held this material: yes | no
- Verified ignored before moving: <command and result>

If Git never held the source material, the private staging copy is the only
copy. Do not delete from it until every ledger row is terminal.

## Scope

What this migration will and will not touch. Name the areas deliberately left
for a later effort.

## Definition Of Done

- Source roots are empty or contain only a redirect stub.
- Every `ledger.md` row has a terminal status.
- Promoted meaning is under a canonical owner and validated.
- Private staging is either retained deliberately or dropped deliberately, recorded here.

## Related

- Task record:
- Triage notes:
- Promotion records:

## Outcome

Fill in at completion: what became canonical, what was rejected, what stayed
private, and where the originals ended up.
