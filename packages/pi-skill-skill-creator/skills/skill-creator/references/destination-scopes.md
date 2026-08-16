# Destination Scopes

Where a new skill is written decides who discovers it. Ambiguous creation never inherits scope from the current working directory: ask once for `Global`, `Project-local`, or `Custom`, resolve to an absolute path, and confirm before writing.

## Scope gate

```text
explicit target path OR existing skill named for modification
  -> normalize and use that target; no scope prompt
ambiguous creation (no target given)
  -> ask once: Global | Project-local | Custom
  -> resolve path for the selected scope
  -> show normalized absolute path, scope, and discovery behavior
  -> check collision and writability
  -> create only after the destination is unambiguous
```

- **Global** — available across all Pi projects on the machine.
- **Project-local** — persistent on disk for the current repository and discovered in later sessions (it is not a temporary or session-only scope).
- **Custom** — a user-supplied path anywhere else.

## Resolution rules

- **Global**: `${PI_CODING_AGENT_DIR}/skills/<skill-name>` when `PI_CODING_AGENT_DIR` is set; otherwise `~/.pi/agent/skills/<skill-name>` (expand `~`; `PI_CODING_AGENT_DIR` overrides Pi's config root, whose default is `~/.pi/agent`). Discovery: automatic, global.
- **Project-local**: walk from the current working directory to the nearest `.git` ancestor; use `<git-root>/.pi/skills/<skill-name>`. With no `.git` ancestor, fall back to `<cwd>/.pi/skills/<skill-name>`. Discovery: automatic once the project is trusted; Pi scans `.pi/skills/` from the working directory upward toward the git root.
- **Custom**: expand `~` and make the user-supplied path absolute; preserve spaces rather than quoting or mangling them. Discovery classification:
  - under the global skills root → globally discovered;
  - under the project's `.pi/skills/` → project-discovered;
  - inside a package's `skills/` tree or `pi.skills` entry → package-managed;
  - anything else → explicit-load-only: requires `pi --skill <path>` (repeatable, additive) or a `skills` entry in `.pi/settings.json` / settings file before Pi loads it.

## Pre-write checklist

1. Display the resolved absolute path and its scope/discovery classification.
2. Destination already contains a `SKILL.md` → switch to existing-skill modification semantics; never silently replace. Report that an existing skill was found.
3. Destination exists but holds a non-skill directory or file → blocking collision; ask for a different target.
4. Destination unwritable or not creatable (permissions, missing parents beyond one level) → report and stop.
5. Only then create the directory and write files.

## Failure branches

- **User does not answer the scope question:** do not guess; treat the missing answer as a stop condition for creation.
- **Ambiguous custom path (relative, or two candidate roots):** ask for an absolute path or an explicit scope instead of resolving by inference.
- **Env var points somewhere unexpected:** surface the resolved path; the user confirms before any write.
