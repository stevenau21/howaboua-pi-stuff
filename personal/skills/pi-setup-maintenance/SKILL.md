---
name: pi-setup-maintenance
description: "Maintains this user's pi skill setup end to end. Use for pulling skill updates, changing or adding personal skills, editing the forked howaboua packages, bootstrapping pi on a new machine, syncing settings across machines, or switching between the fork and the published npm packages. Not for general skill authoring, which belongs to skill-creator."
---

# Pi Setup Maintenance

Runbook for the fork-based pi skill setup. Machine-agnostic; paths use `~` (= `%USERPROFILE%` on Windows).

## Layout

| Piece | Location | Role |
|---|---|---|
| Upstream repo | `github.com/IgorWarzocha/howaboua-pi-stuff` | Canonical source of the `@howaboua/pi-*` packages, incl. `pi-skill-skill-creator` |
| Fork | `github.com/stevenau21/howaboua-pi-stuff` | Working state; `main` always deployable |
| Runtime clone | `~/.pi/agent/skills-src/howaboua-pi-stuff` | What pi actually loads; pull-only, never author here |
| Dev clone | e.g. `F:\projects\howaboua-pi-stuff` (desktop) | Where changes are authored; `origin`=upstream, `fork`=fork |
| Settings | `~/.pi/agent/settings.json` (synced via private `stevenau21/pi-config`) | Records the relative package paths below |

Packages loaded from the runtime clone (relative to `~/.pi/agent`, machine-independent):

- `skills-src\howaboua-pi-stuff\packages\pi-skill-skill-creator` — forked package carrying our resource-graph + destination-scope upgrade (upstream PR pending; not yet in npm)
- `skills-src\howaboua-pi-stuff\personal` — personal skills package (this skill)

Everything is in-place loading: edits in the runtime clone appear after a pi restart, no reinstall.

## Update skills (routine)

```bash
cd ~/.pi/agent/skills-src/howaboua-pi-stuff
git pull --ff-only
```

Restart pi. Verify: `pi list` shows both paths resolving under `~/.pi/agent/skills-src/`.

## Change a forked package (under `packages/`)

Work in the dev clone:

1. `git checkout main && git pull fork main` (fallback: `fork/skill-creator-resource-graph` until `main` is resynced to upstream).
2. Branch: `git checkout -b <topic>`.
3. Edit under `packages/<pkg>/`. Validate before committing:
   `python packages/pi-skill-skill-creator/skills/skill-creator/scripts/skill-efficiency-check.py <skill-dir> --host pi --strict`
   and, when evals changed, `python packages/pi-skill-skill-creator/skills/skill-creator/scripts/run-skill-evals.py --cases <cases.json>`.
4. Shipped package changes require a changeset (`.changeset/patch-*.md`, `"@howaboua/<pkg>": patch`).
5. Contribute: push the branch, open a PR to `IgorWarzocha/howaboua-pi-stuff` (never include `personal/`).
6. Deploy regardless of PR outcome: `git push fork <topic>:main`, then update the runtime clone (see Update skills) on each machine.

Keep `main` on the fork as the single deployable line; topic branches exist for PRs.

## Add or change a personal skill (under `personal/`)

1. Dev clone, branch off `fork/main`.
2. One folder per skill: `personal/skills/<skill-name>/SKILL.md` (frontmatter: kebab-case `name`, quoted `description` with job + "Use for" triggers + key exclusions). Optional `references/`, `scripts/`, `assets/`, `evals/`; every file reachable from `SKILL.md`.
3. For a new skill consider `/skill:skill-creator` for authoring depth.
4. Validate non-strict (runbooks may lack references or scripts folders): run the checker from Update-skills paths without `--strict`.
5. Commit, `git push fork <branch>:main`, pull on each machine, restart pi. New skills under `personal/` are discovered via its `pi` manifest — no settings.json change.

## Bootstrap a new machine

```bash
git clone --depth 5 https://github.com/stevenau21/howaboua-pi-stuff.git "%USERPROFILE%\.pi\agent\skills-src\howaboua-pi-stuff"
```

Restore `~/.pi/agent/settings.json` from `stevenau21/pi-config`; it already contains both relative package entries. Restart pi, `pi list` to verify.

## Switch to published npm packages

When upstream merges and `npm view @howaboua/pi-skill-skill-creator version` exceeds 0.0.5, per machine:

```bash
pi remove skills-src\howaboua-pi-stuff\packages\pi-skill-skill-creator
pi install npm:@howaboua/pi-skill-skill-creator
```

Keep the `personal` entry. Then resync the fork: `git fetch origin && git checkout -B resync origin/main`, carry `personal/` over (e.g. `git checkout fork/main -- personal/`), force-push `fork resync:main`, re-clone runtime copies without `--depth` limitations if needed.

## Recovery

- **Skill not loading:** `pi list`; if missing, `git -C ~/.pi/agent/skills-src/howaboua-pi-stuff pull --ff-only`; check `settings.json` entries are the exact relative paths above.
- **Runtime clone dirty/broken:** it holds no authored work — `git reset --hard origin/main && git clean -fd` (origin = the fork).
- **Must change a skill now with no dev clone:** author in the runtime clone, push to fork `main`, then re-clone cleanly on next chance.
- **Force-load this runbook:** `/skill:pi-setup-maintenance`.
- **Settings lost:** pull `pi-config`; entries are the two relative paths in Layout.

## Output

Report: what changed (files/commits), validation run, machines still needing `git pull` or restart, and whether any upstream PR state moved.
