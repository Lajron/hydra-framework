# Wiki Authoring Skill

## Capability

Draft or update a human-facing `project-wiki/` page as an AI agent, keeping
the wiki a readable map over canonical Hydra sources rather than a second
source of truth.

## Procedure

1. Read the relevant canonical sources before drafting: the subject area's
   `.hydra-framework/repo/knowledge/` files or code that owns the
   behavior being described.
2. Update the canonical file first when a rule, policy, or behavior needs to
   change. Never let the wiki assert something the canonical source does
   not yet say.
3. Keep pages short enough for a human to read in one sitting; link exact
   rules instead of restating them.
4. Cite sources near durable claims: an inline link or a nearby `Sources`
   list pointing at the canonical owner. Never cite `.hydra-framework.local/`
   from a shared wiki page; inline the durable content instead.
5. Record gaps explicitly (what's checked, what's missing, what's next)
   instead of smoothing over a mismatch between the wiki and its source.
6. Write like an engineer stating how the system works, not like a log of
   the research done to write the page: no command-plus-date sentences, no
   "Source Notes" section reciting what was checked, no em dashes. See
   `core/agent-writing.md` for runtime text; wiki prose follows the linked
   documentation-authoring guide.
7. Run `hydra.py validate-wiki` after edits, and `hydra.py validate` if the
   change touched anything under `.hydra-framework/`.
8. Build or repair one page at a time unless a larger rewrite has an approved
   plan behind it.

## Output

Report the page changed, canonical sources cited, known gaps, and validation
evidence.

## Boundaries

- Do not let the wiki become a second source of truth. Update its canonical source first when behavior changes.
- Do not cite `.hydra-framework.local/` from a shared wiki page. Inline the safe durable content instead.
- Do not rewrite several pages without an approved plan. Build or repair one page at a time.

## Related

See `.hydra-framework/surfaces/README.md` (Wiki Surface) for the citation
rules and audience contract this procedure implements, and
`project-wiki/hydra-framework/reference/documentation-authoring.md` for
visual grammar and color/state conventions.
