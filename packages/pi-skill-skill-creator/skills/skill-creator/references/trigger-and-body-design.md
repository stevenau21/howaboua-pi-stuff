# Trigger and Body Design

## What a skill is

A skill is a portable instruction bundle that teaches an agent a repeatable workflow. It answers six questions: what problem it solves; when the host activates it; what steps the agent follows; which tools, files, or references are used; what success looks like; how failures are recovered. A skill is a compact operational contract, not just a prompt.

Create one when the task recurs, the workflow has recognizable steps, output quality improves with reused structure, and domain rules, validation, or examples help. Do not create one for a one-off task, an empty abstraction, or a workflow still fundamentally unclear.

## Explicit triggering

A skill is useful only if it loads when needed and stays quiet when irrelevant. The description MUST encode: what the skill does, when to use it, trigger phrases or situations, and relevant artifact types. Where collision is likely, add when NOT to use it. Descriptions are semantic indexes, not prose introductions.

## Writing descriptions

Reliable shape:

> **[Job or outcome]. Use for/when [triggers, artifacts, situations].**

Boundary only for likely collisions:

> **[Job]. Use for [trigger A], [trigger B]. Not for [adjacent task].**

Good:

```yaml
description: "Sprint planning and backlog breakdown. Use for prioritization, ticket decomposition, scope estimates, or capacity planning."
```

```yaml
description: "PDF contract review: obligations, risks, renewals, missing clauses. Use for contract analysis or clause extraction. Not general PDF summaries."
```

Bad: `"Helps with projects."` (category, not job); `"Implements the project entity model with hierarchical relationships…"` (architecture-centric, not user-trigger-centric); `"Transforms messy ideas into powerful, crystal-clear plans…"` (atmospheric; weak retrieval terms).

Under-triggering → expand with more concrete tasks and wording variants. Over-triggering → tighten scope and add exclusions for plausible neighbors.

## The body

The body starts where execution starts. Never add `Purpose`, `When to use`, `Do not use when`, `Activation`, `Triggers`, or equivalents—the description already owns selection semantics.

Register matches task. SOP, coding, tooling, review: terse imperatives, decisions, constraints, commands, checks; fragments fine. Creative generation: evocative language where it steers voice, imagery, or taste; operational boundaries stay clear. Descriptions: always denotative and terse.

Consider only when it changes execution: prerequisites; expected inputs; exact steps; validation gates; output contents; common failures and recovery.

Adaptable layout (add sections only when they change behavior or remove ambiguity):

```markdown
# Skill Title

## Workflow
## Inputs
## Prerequisites
## Validation
## Recovery
## Output
## Examples
```

## Anti-patterns

- **Vague description** — a category, not a job.
- **Tool-centric framing** — users ask for outcomes, not internal architecture.
- **Monolithic SKILL.md** — giant manuals hurt triggering and execution.
- **Missing negative scope** — adjacent skills collide.
- **Hidden assumptions** — unstated services, runtimes, or files fail unpredictably.
- **Unclear success** — without a stated completion condition the agent improvises; simple conversational skills need no ceremonial output contract.
- **Missing decision examples** — one well-chosen example resolves ambiguous judgment or output shape; examples that restate the workflow only burn context.
- **Decorative prose** — descriptions never need voice; operational bodies are direct. Remove sales language, reassurance, imagery, filler.
