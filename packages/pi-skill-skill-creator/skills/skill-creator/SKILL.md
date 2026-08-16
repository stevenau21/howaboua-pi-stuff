---
name: skill-creator
description: "Reusable skill design and maintenance. Use for SKILL.md creation, trigger design, body structure, supporting files, validation, consolidation, or cross-agent ports. Not for one-off prompt edits or passive documentation."
---

# Skill Creator

Creates and audits skills as connected instruction bundles: every supporting file reachable from `SKILL.md`, loaded under a stated condition, consumed by a workflow step, and covered by validation.

## Inputs

Required:

- the workflow or recurring problem the skill should handle
- the target path, or enough workspace context to infer it

Useful when available:

- an existing skill and all of its supporting files
- representative user requests, failures, or corrections
- host documentation and nearby skill conventions

## Host profile

Every skill is validated against a host profile that owns frontmatter limits, allowed fields, and supporting-directory rules. This bundle ships `assets/host-profiles/pi.json` (default) and `assets/host-profiles/generic.json` for host-neutral SKILL.md conventions. Load `references/host-profiles.md` when the target host is not Pi, when profile fields are questioned, or when adding a profile for a new host.

## Resource map

| Resource | Load when | Consumed by |
|---|---|---|
| `references/skills-reference-guide-for-agents.md` | Routing: pick focused references by task branch | every task entry point |
| `references/destination-scopes.md` | Creating a new skill without an explicit target | stage 2 |
| `references/trigger-and-body-design.md` | Writing or revising description or body | stages 5, 6 |
| `references/workflow-resource-graph.md` | Designing stages, handoffs, or the file graph | stages 4, 5, 8 |
| `references/supporting-files.md` | Splitting detail into `references/`, `scripts/`, `assets/`, `evals/` | stage 6 |
| `references/host-profiles.md` | Host is not Pi, or profile limits are questioned | stages 3, 7 |
| `references/testing-and-evaluation.md` | Building trigger/execution cases or fixtures | stage 8 |
| `references/packaging-and-lifecycle.md` | Publishing, versioning, or rolling back | stage 9 |
| `references/safety-and-recovery.md` | Destructive scope, secrets, or provenance is in play | stages 5, 8 |
| `scripts/skill-efficiency-check.py` | Structural validation run | stages 7, 9 |
| `scripts/run-skill-evals.py` | Behavioral fixture validation run | stage 8 |
| `evals/cases.json` | Behavioral coverage for this skill itself | stage 8 |

## Workflow

Each stage names its contract: **consumes → produces → used by → failure branch**.

1. **Ground the task.**
   - Consumes: user request, existing skill tree. Produces: concrete use cases. Used by: stages 2–6.
   - Read the existing `SKILL.md` and every file it directs the agent to read before deleting, merging, or restructuring.
   - Verify host format rules, real tool names, commands, and paths against host documentation or `references/host-profiles.md`—not memory.
   - Reduce a vague request to 2–3 concrete use cases (goal, trigger, inputs, workflow, result) before drafting.
   - Failure branch: inputs stay vague → ask for or construct concrete requests; do not draft yet.

2. **Resolve the destination scope.**
   - Consumes: user request, workspace context. Produces: unambiguous destination path with scope and discovery classification. Used by: stage 6.
   - Creating a new skill with no explicit target: ask once — `Global`, `Project-local`, or `Custom`. Never infer scope from the current working directory. Load `references/destination-scopes.md` for resolution rules.
   - Global resolves to `${PI_CODING_AGENT_DIR}/skills/<name>` when `PI_CODING_AGENT_DIR` is set, else `~/.pi/agent/skills/<name>`. Project-local resolves to `<nearest-git-root>/.pi/skills/<name>` (cwd fallback when no `.git` ancestor). Custom requires a user-supplied path, classified as globally discovered, project-discovered, package-managed, or explicit-load-only (`pi --skill <path>` / settings entry).
   - Before writing: show the resolved absolute path and scope. Destination already holds a `SKILL.md` → switch to modification semantics, never replace. Non-skill collision or unwritable destination → blocking; ask for a different target.
   - Failure branch: no scope answer or ambiguous path → stop and ask; do not create by inference.
   - Explicit target paths and requests to modify an existing skill bypass the prompt entirely.

3. **Select the host profile.**
   - Consumes: target host knowledge. Produces: profile choice (Pi default, `generic`, or a custom JSON per the profile contract). Used by: stages 5–7.
   - Failure branch: host unverified → use `generic`, state the assumption, and mark host-specific fields as unverified in the report.

4. **Decide whether a skill is the right artifact.**
   - Consumes: use cases. Produces: artifact decision. Used by: stage 5.
   - Use a skill for a recurring task where reusable instructions, judgment, examples, or helpers improve execution; use documentation for passive reference without a repeatable workflow.
   - Failure branch: no recurrence or no agent workflow → propose documentation or a workspace SOP instead; stop.

5. **Map the workflow and resource graph.**
   - Consumes: use cases, artifact decision. Produces: ordered stages with handoffs (`consumes → produces → used by → failure branch`) and a file graph. Used by: stages 6–8.
   - One supporting file per load condition; name each file's condition and consumer at the step that loads it.
   - Failure branch: a stage has no consumer for its output → merge or delete it.

6. **Author the bundle.**
   - Consumes: stage map, profile, destination, resource graph. Produces: `SKILL.md` plus supporting files at the resolved destination. Used by: stages 7–9.
   - Core workflow and load-bearing judgment stay in `SKILL.md`; conditional depth moves to `references/`, deterministic checks to `scripts/`, static inputs to `assets/`, behavioral cases to `evals/`.
   - Description is a semantic index: job, activation conditions, likely request language, artifacts, only necessary exclusions. No mood, rationale, or tutorial prose.
   - Do not add `Purpose`, `When to use`, `Activation`, `Triggers`, or equivalent headings; the description owns selection semantics.
   - State autonomy, approval, and safety boundaries once, near the action they govern.
   - Failure branch: instructions drift or duplicate → cut accumulation, keep verified judgment; re-run stage 5 if structure no longer matches.

7. **Validate structure.**
   - Consumes: authored bundle. Produces: validator report. Used by: stages 8, 9.
   - Run `python scripts/skill-efficiency-check.py <skill-dir>` with `--host <profile>`; add `--strict` before packaging and `--format json` for tooling.
   - Failures (dangling, escaping, case-mismatched, or cyclic references) are structural: fix, do not ship. Orphan warnings fail under `--strict`—link the file or delete it.
   - Failure branch: validator reports profile errors → fix profile JSON per the closed schema; structural issues → repair links or remove files.

8. **Evaluate behavior.**
   - Consumes: validator-clean bundle. Produces: eval fixtures (`evals/cases.json` schema) and results. Used by: stage 9.
   - Validate fixtures deterministically: `python scripts/run-skill-evals.py --cases <file>`; cover obvious and paraphrased triggers, neighboring non-triggers, all destination branches and explicit-target bypass, creation, audit, missing inputs, broken paths, unsafe scope, repeated runs, and script failure.
   - Live runs are opt-in via `--adapter <command>`; the adapter exchanges JSON and returns normalized observations. Do not make package checks depend on a model.
   - Failure branch: fixture schema invalid → fix schema; adapter run flakes → treat as advisory, never as a release gate.

9. **Audit traceability and finish.**
   - Consumes: reports from stages 7–8. Produces: packaged change and report. Used by: user.
   - Final audit: map each use case to workflow step → resource → load condition → validation → recovery. Every supporting file must appear; remove entries with no consumer.
   - Report changed files, destination and scope, validation performed, and intentional warnings.
   - Make in-scope, low-risk edits directly; ask before destructive changes, external writes, or material scope expansion.
   - Failure branch: audit finds an unlinked file or unstated condition → return to stage 5 for that file; do not weaken the check.

## Validation checklist

- Workflow teaches a recurring task; description fully carries job, triggers, and necessary boundaries.
- Destination was resolved explicitly—no scope inferred from cwd—and confirmed before writing.
- Each supporting file is reachable from `SKILL.md`, loaded under a stated condition, and consumed by a named step.
- Handoffs name consumes, produces, used by, and failure branch.
- Host constraints and runtime assumptions come from the selected profile or verified host documentation.
- Efficiency check passes; strict run is clean before packaging; eval fixtures validate deterministically.
- Accumulation (duplicate guidance, generic quality prose, restated examples) removed before shipping.

## Recovery

- **Workflow is vague:** reduce to concrete requests, inputs, decisions, and results before drafting.
- **Triggering is unreliable:** revise the description with real user language and adjacent non-triggers.
- **Destination is ambiguous or collides:** re-run the scope gate; existing skill → modify, non-skill collision → pick another target.
- **Validator flags a cycle:** keep links one-directional from `SKILL.md` outward; replace back-links with routing via the root.
- **Orphan warning:** link the file from the step that consumes it, or delete it; do not leave silent files.
- **Case mismatch on Windows:** match on-disk casing exactly; the validator compares segment by segment.
- **Profile JSON rejected:** the schema is closed—remove unknown keys and re-check limits.
- **A deterministic rule stays fuzzy:** encode it in a script when that is simpler and more reliable than prose.
- **Upstream material is bloated or doctrinal:** keep verified workflow knowledge and rebuild around the target host and users.

## Output

A completed pass leaves a valid, connected, packaged skill at an explicitly confirmed destination: reliable trigger description; workflow stages with explicit handoffs; every supporting file reachable, conditioned, consumed, and validated; plus a concise record of validation and intentional tradeoffs.
