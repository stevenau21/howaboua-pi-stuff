# Workflow and Resource Graph

A skill is a directed graph of instructions: `SKILL.md` is the root; references, scripts, assets, and evals are nodes; links and path mentions are edges. Every node must be reachable, loaded under a stated condition, consumed by a workflow stage, and covered by validation.

## Stage contract

Each workflow stage names four things:

- **consumes** — inputs it reads
- **produces** — artifacts or decisions it emits
- **used by** — the stage(s) that need the product
- **failure branch** — what happens and where control goes when the stage fails

A stage whose output has no consumer is dead weight; merge or delete it.

## Link contract

Every link from `SKILL.md` (or from a reference) to a supporting file states, near the step that loads it:

- exact path (`references/api-patterns.md`, never "the docs folder")
- required or conditional load
- load condition (when this file is needed)
- consumer/output (which step uses it and what it produces)
- validation or recovery behavior if the file is missing or wrong

Graph rules enforced by structural validation:

- links resolve inside the skill root; `..` escapes and absolute paths fail
- missing targets, file/directory mismatches, and case mismatches fail on all platforms (casing is compared segment by segment, so Windows still catches `Other.md` vs `other.md`)
- reference cycles fail: links run one-directional from `SKILL.md` outward; route through the root instead of linking back
- unreachable supporting files warn by default and fail with `--strict`: link them or delete them

## Authoring procedure

1. **Confirm skill fit** — recurrence, multi-step or rule-heavy workflow, consistency value, examples/validation help. Too vague → reduce to 2–3 concrete use cases first.
2. **Define use cases** — for each: goal, trigger, inputs, workflow, result.
3. **Map the workflow** — ordered stages (fetch/inspect, validate, transform, decide, generate, review, save/publish, confirm) with the stage contract above; define stop or recovery behavior where failure would cause incorrect continuation, repeated work, or unsafe side effects.
4. **Define the output contract before writing instructions** — e.g. markdown report with sections A–E; JSON matching schema X; tickets with title/estimate/owner/link; transformed CSV plus validation report.
5. **Draft frontmatter** — name and description only after use cases are clear.
6. **Draft the body** — register chosen first; numbered steps, checklists, exact paths, explicit conditions.
7. **Add supporting files** — one load condition per file; heavy detail to references, deterministic logic to scripts, static inputs to assets, behavioral cases to evals.
8. **Test and tighten** — a few representative trigger, non-trigger, execution, and failure cases; broaden only when repeated real failures justify it.

## Instruction writing rules

**Specific and actionable.** "Validate the data" → list the exact checks (columns, formats, ranges) and what to do on failure.

**Critical rules near the top** — don't bury essential conditions mid-narrative.

**Separate policy from procedure.**

```markdown
## Validation policy
- Do not create tickets without a title and owner.

## Procedure
1. Parse the backlog.
2. Check title, owner, acceptance criteria.
3. Blocked items → return list; only then create tickets.
```

**Stop conditions** — when to stop iterating, iteration caps, stop before dependent side effects when a connection or auth fails.

**Idempotence where relevant** — update-on-identifier-match; no duplicate records; version-suffix generated files.

## High-value patterns

- **Sequential orchestration** — gather → validate → A → B(uses A) → validate → finalize. For onboarding, ticket creation, provisioning.
- **Multi-tool coordination** — fetch A → transform → push B → notify C → log D, with explicit phase boundaries, data handoffs, and rollback for partial failure.
- **Iterative refinement** — draft → checklist → fix specific defects → revalidate → stop at criteria. For reports, docs, code with lint/test loops.
- **Context-aware tool selection** — inspect file type/size/destination → choose by explicit criteria → proceed with tool-specific steps.
- **Domain guardrails** — collect facts → apply domain rules → approve/reject/route → document. For compliance, QA, policy, review.
- **Validate before consequential work** — validate before side effects when bad input is common and proceeding wastes work or causes damage; not as a universal diagnostics-first ritual.
- **Extract-transform-generate** — extract → canonical form → generate → final checks. For document generation, data pipelines, repackaging.

## Traceability audit

Before shipping, map every requirement and use case to: workflow step → resource → load condition → validation → recovery. Every supporting file must appear; every file must have a consumer. Unstated condition or missing consumer → fix the graph, not the checklist.
