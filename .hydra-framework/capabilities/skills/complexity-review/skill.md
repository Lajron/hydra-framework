# Complexity Review Skill

## Capability

Review changed code or a scoped repository area for over-engineering only. The output is a ranked delete-or-simplify list, not a general correctness review.

## Procedure

1. Establish scope: current diff by default, or the user-specified files, module, or repository area.
2. Inspect the scoped code and nearby repository patterns. Prefer `git diff`, `rg`, and direct file reads.
3. Flag only concrete complexity reductions that keep required behavior intact. Use these tags:
   - `delete`: dead code, speculative feature, unused flexibility, redundant adapter, or obsolete path.
   - `stdlib`: hand-rolled behavior that a standard library or built-in tool already covers.
   - `native`: custom code or dependency replaced by a framework, platform, browser, database, or shell feature.
   - `yagni`: abstraction, configuration, option, layer, interface, or factory with no current second use.
   - `shrink`: same behavior with fewer local lines or fewer touched files.
4. Do not flag safety, validation, accessibility, migration, observability, or data-loss protection as bloat unless it is provably redundant. A guard that looks redundant is often the only detection method for a failure that otherwise passes silent. When the scope includes Hydra's own machinery, check `.hydra-framework/repo/knowledge/silent-failure-modes.md` before proposing a deletion.
5. For each finding, name the location, what to remove or replace, and the simpler replacement.

## Output

Use one line per finding:

`<path>:L<line>: <tag>: <what to cut>. <replacement>.`

End with `net: -<N> lines possible` when there is enough information to estimate it. If nothing concrete should be cut, say `Lean already. Ship.`

## Boundaries

- This skill reports; it does not apply edits unless the user asks.
- Correctness bugs, security holes, and performance risks belong in a normal review pass. Mention them only when they directly affect whether a proposed simplification is safe.
- Do not invent a baseline savings number for code that was never written.
