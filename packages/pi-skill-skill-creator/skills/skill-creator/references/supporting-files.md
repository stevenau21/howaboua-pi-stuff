# Supporting Files

## Progressive disclosure

Reveal information in layers: frontmatter indexes job and activation; the body executes the workflow; linked files hold depth. Frontmatter terse and trigger-focused, body operational, dense conditional material in supporting files.

## Determinism where it matters

Natural language is flexible; workflows are not. Make critical behavior deterministic: preconditions, validation rules, step order, stop conditions, output contracts, error handling. If a check can be code, a script usually beats prose.

## Deliberate context

Carry the smallest body that reliably preserves job and judgment. Shorter is not automatically better—removing trigger coverage, edge cases, or domain rules makes a skill cheaper and worse. Keep normal execution in the skill root; conditional depth in references; remove repeated reminders before removing material that helps weaker or context-poor models.

## Anatomy

```text
your-skill/
├── SKILL.md              # required: frontmatter + operational body
├── references/           # consult-on-demand knowledge
│   ├── api-patterns.md
│   └── examples/
├── scripts/              # deterministic helpers
│   └── validate.py
├── assets/               # static inputs (templates, samples)
│   └── template.md
└── evals/                # behavioral cases and fixtures
    └── cases.json
```

Every file must be reachable from the skill root, directly or through references; each states its load condition and consumer at the step that loads it.

## References/

API conventions, rate limits, pagination rules, schemas, field definitions, error-recovery notes, domain terminology, worked examples. One topic per file; short sections; headings mirror likely questions; examples near the rule. Never move core workflow instructions here if the agent always needs them—core procedure lives in the skill root.

## Scripts/

Validation, transformation, formatting, strict parsing, schema enforcement, machine-readable post-processing.

Rules: explicit arguments; no interactive prompts; stable exit codes; predictable stdout; diagnostics to stderr; documented dependencies; deterministic for the same input. MUST NOT hide destructive side effects, depend on manual intervention, or require undocumented environment setup.

Document near the use site: invocation, arguments, outputs, exit codes, side effects, failure behavior.

```markdown
Run `python scripts/validate.py --input <file>`.
- exit 0: passed; exit 1: validation failed; exit 2: execution error
- stdout: JSON summary
If exit 1, do not proceed with generation.
```

Do not add a script for sophistication's sake; plain instructions suffice when they are reliable. Structural validation never executes bundled scripts.

## Assets/

Templates, skeletons, sample files, style guides, boilerplate. If the workflow expects a template, say so where the template is loaded.

## Eval fixtures/

Behavioral cases follow the fixture schema (see the testing reference). Ship them in the bundle so evaluation is reviewable and repeatable.

## Skeleton

```markdown
---
name: example-skill
description: "[Job/outcome]. Use for [triggers, artifacts, situations]."
---

# Example Skill

## Workflow
1. Inspect [relevant inputs or existing state].
2. Decide [load-bearing judgment].
3. Perform [core action].
4. Verify [observable success condition].

<!-- Add only when useful:
## Inputs  ## Prerequisites  ## Validation
## Recovery  ## Output  ## Examples
-->
```
