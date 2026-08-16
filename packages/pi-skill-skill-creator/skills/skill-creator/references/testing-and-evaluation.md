# Testing and Evaluation

Choose coverage by risk, complexity, and observed failure modes—these are a menu, not a mandatory harness for every edit.

## Testing strategy

- **Trigger tests** — loads when relevant, quiet when irrelevant: obvious triggers, paraphrased triggers, non-triggers.
  - should trigger: "plan this sprint"; "break this work into tickets"; "organize backlog items for next week"
  - should not: "what is the weather"; "explain recursion"; "generate a photorealistic image"
- **Functional tests** — happy path, missing input, invalid input, tool failure, repeated run, unusual-but-valid edge case.
- **Output quality** — required sections exist; formatting stable; fields complete; links and paths resolve; artifacts valid.
- **Efficiency** — when it matters, compare with/without the skill: tool calls, retries, context consumed, user corrections.

## Practical method

Solve one difficult real example manually, then extract the winning pattern into the skill. This exposes true edge cases, actual step order, and what the agent needed to know—grounded instead of imagined. Broaden the set only enough to cover materially different requests and failures.

## Fixture schema (cases JSON)

Behavioral coverage lives in an eval fixtures file (`cases.json` under the skill's `evals/`):

```json
{
  "schema_version": 1,
  "cases": [
    {
      "id": "kebab-case-id",
      "kind": "trigger | execution | recovery | portability",
      "request": "representative user request",
      "expect": {
        "activated": true,
        "artifacts_present": ["SKILL.md"],
        "artifacts_absent": ["debug.log"],
        "diagnostics_present": ["regex"],
        "diagnostics_absent": ["regex"],
        "forbidden_actions": ["force-push"]
      }
    }
  ]
}
```

`activated` is required. `diagnostics_*` entries are regexes matched against the run's reported diagnostics and errors—structural assertions, never exact model prose. `forbidden_actions` are substrings banned from observed actions. Cover, at minimum: obvious trigger, paraphrased trigger, neighboring non-trigger, every destination branch (Global, Project-local, Custom) plus explicit-target bypass, creation, audit/refactor, missing inputs, broken supporting paths, unsafe/destructive scope, repeated run/idempotence, script failure, cross-industry portability.

Deterministic validation runs offline and never invokes a model:

```bash
python scripts/run-skill-evals.py --cases evals/cases.json
```

## Live adapter contract (opt-in)

A live harness exchanges JSON over a subprocess; normal package checks never depend on a model:

- the runner sends one case JSON object on stdin
- the adapter prints one normalized observation object per line on stdout: `{id, activated, actions?, artifacts?, diagnostics?, errors?}`
- `id` must echo the case id; `activated` must be boolean
- malformed output, wrong/missing id, timeout, or nonzero adapter exit are execution failures for that case

```bash
python scripts/run-skill-evals.py --cases evals/cases.json --adapter "node harness.mjs" --timeout 60
```

A verified Pi harness can implement the adapter by running the skill against the case request and normalizing what happened; it must not embed credentials or provider dependencies. Observations are matched structurally (activation boolean, required artifacts, diagnostics regexes, prohibited actions)—never by exact prose. Reports redact secrets; keep full prompts and credentials out of fixtures and reports. Treat live results as advisory; the deterministic fixture check remains the release gate.

## Troubleshooting

- **Skill does not load** — description lacks the concrete job or request language; then check frontmatter, discovery location, exact `SKILL.md` naming, host naming rules, collisions.
- **Loads too often** — narrow category language to tasks, artifacts, outcomes; add negative scope for plausible neighbors; compare with overlapping skills.
- **Loads but ignored** — move critical rules near the action they govern; make ordering explicit; replace vague verbs with observable conditions; add one example only if ambiguity remains.
- **Tool calls fail** — verify exact tool names, permissions, inputs, return shapes. Record load-bearing prerequisites; avoid diagnostics-first preflights when trying the safe operation reveals availability directly.
- **Output inconsistent** — clarify success condition and decision rules; add targeted validation, one representative example, or a deterministic script for the actual source of variation.
- **Context bloat** — remove repeated guidance and examples first; keep normal execution in the root, conditional depth in references; preserve judgment-changing material.
