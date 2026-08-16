# @howaboua/pi-skill-skill-creator

Designs, audits, refactors, validates, and packages reusable agent skills as connected instruction bundles: every supporting file reachable from `SKILL.md`, loaded under a stated condition, consumed by a workflow step, and covered by validation.

## Install

```bash
pi install npm:@howaboua/pi-skill-skill-creator
```

Use it for `SKILL.md` trigger descriptions, progressive disclosure, supporting references/scripts/assets, resource-graph validation, evaluation fixtures, destination-scope routing (Global, Project-local, Custom), consolidation, or porting between agent harnesses. It is not for one-off prompt edits or passive documentation with no repeatable workflow.

## Destination scopes

When a new skill has no explicit target, the workflow asks once for `Global`, `Project-local`, or `Custom`—never inferring scope from the current directory. Global resolves to `${PI_CODING_AGENT_DIR}/skills/<name>` (default `~/.pi/agent/skills/<name>`); Project-local to the nearest git root's `.pi/skills/<name>`; Custom to a user path classified by how Pi discovers it (including explicit `pi --skill <path>`). The resolved path and scope are shown before anything is written, and an existing `SKILL.md` at the destination switches to modification semantics instead of replacement. See `skills/skill-creator/references/destination-scopes.md`.

## Structural validation

```bash
python skills/skill-creator/scripts/skill-efficiency-check.py <skill-dir-or-SKILL.md>
```

Checks frontmatter against a host profile, extracts the local resource graph (Markdown links and exact path mentions outside fenced code), and reports:

- **Issues** (exit 1): dangling references, path escapes and absolute paths, directory-target links, case mismatches (segment-by-segment, so Windows still catches them), reference cycles with the full path, malformed host profiles.
- **Warnings**: orphaned supporting files not reachable from `SKILL.md`. Fail under `--strict`; warn otherwise.
- **Suggestions**: missing references/scripts, long descriptions, frontmatter fields outside the profile's allowed set.

Flags:

- `--host {generic,pi}` — select the host profile (`pi` default; `generic` for host-neutral conventions). `--profile <path>` uses a custom profile JSON; the schema is closed, unknown keys are rejected.
- `--strict` — treat warnings as failures; recommended before packaging.
- `--format json` — machine-readable report (profile, nodes, edges, external links, issues, warnings, suggestions, summary).

The validator never executes bundled scripts or fetches external URLs.

## Behavioral evaluation

```bash
python skills/skill-creator/scripts/run-skill-evals.py --cases evals/cases.json
```

Validates evaluation fixtures offline (schema, unique ids, structural expectations) and reports coverage — no model required. Live runs are opt-in via an adapter that reads one case JSON on stdin and prints one normalized observation object:

```bash
python skills/skill-creator/scripts/run-skill-evals.py --cases evals/cases.json --adapter "node harness.mjs" --timeout 60
```

Adapter failures (malformed output, wrong id, timeout, nonzero exit) fail the case; secrets are redacted from reports. Live results are advisory and never gate a release.

## Package scripts

- `npm run check` — strict self-validation of the bundled skill under the `pi` profile.
- `npm test` — validator and evaluator contract tests (requires Python 3 and Node).

## Host profiles

`skills/skill-creator/assets/host-profiles/pi.json` and `generic.json` own the host-specific rules (frontmatter fields, name/description limits, supporting directories, ignored paths). Add a profile JSON for a new host rather than encoding guesses in prose; see `skills/skill-creator/references/host-profiles.md` for the schema.
