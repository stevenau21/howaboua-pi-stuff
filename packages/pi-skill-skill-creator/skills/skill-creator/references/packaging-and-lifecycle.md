# Packaging and Lifecycle

## Packaging guidance

- The skill lives in a single folder; `SKILL.md` at the root; supporting material under that root; every file reachable from the root.
- Keep the folder clean—no caches, scratch files, or local paths.
- A human-facing repository README MAY sit outside the skill folder; agent-relevant documentation stays in the skill root and its references.
- Never ship local paths, personal names, machine assumptions, or private workflow details; skills must work for any user.

## Pre-package gates

Run before every release; a package that fails these is not releasable:

1. **Strict structural validation** — `python scripts/skill-efficiency-check.py <skill-dir> --host <profile> --strict`: zero issues, zero warnings (no orphaned resources).
2. **Deterministic evaluation** — fixture schema validates offline; behavioral coverage spans trigger, non-trigger, execution, failure, and repeated-run cases.
3. **Dry-pack inspection** — pack the artifact, list its files, and confirm every profile, reference, eval fixture, asset, and script appears; then validate the skill from the extracted tarball directory.

Live adapter runs are advisory and never gate a release.

## Versioning

- Follow the host/repository release process rather than editing generated changelogs by hand.
- Patch for behavior-preserving additions and fixes visible to users; minor for new capability; follow the repository's classification when maintainers disagree.
- Record user-visible behavior changes in a changeset or release note with concrete language—no "upcoming release" speculation.

## Rollback

- Revert the release commit and republish the last known-good version per repository policy; do not patch over a bad release with a hotfix unless policy requires it.
- Users hitting new strict diagnostics can drop `--strict`; structural failures (broken or escaping links) must not be suppressible by design.
- Do not patch installed artifacts as migration. Install the released package and compare its self-validation output before replacing the prior version.

## Final review

**Structure** — name follows host format and length; `SKILL.md` at root; valid frontmatter; required fields; all files reachable; no cycles; no orphans.

**Trigger quality** — description states job, when to use, concrete request language; not too broad; exclusions where collisions are plausible; terse, denotative, no introductory prose.

**Instruction quality** — ordered workflow; validation and failures handled where consequential; success condition stated where needed; examples teach distinct decisions; supporting paths resolve; body does not restate activation semantics; register terse for operational skills, evocative only where it steers creative output.

**Operational quality** — load-bearing prerequisites documented; scripts have clear contracts (invocation, args, outputs, exit codes, side effects); deterministic checks in code; no unstated critical assumption.

**Behaviour quality** — obvious and paraphrased triggers work; unrelated requests do not trigger; invalid/missing input handled proportionately; repeated runs avoid uncontrolled duplicates; accumulation trimmed before useful judgment.

Optimize for reliable activation and execution first; then remove text that no longer changes behavior.
