# Host Profiles

A host profile owns everything host-specific about a skill: allowed and required frontmatter, name pattern and length, description limits, supporting directories, ignored paths, and severity of optional checks. Universal rules (graph reachability, no path escapes, no cycles, casing) live in the validator itself and apply to every host.

## Shipped profiles

- **pi** (default): Pi skill format. `name` and `description` required; optional `license`, `compatibility`, `metadata`, `allowed-tools`, `disable-model-invocation`; name ≤ 64 chars lowercase kebab-case; description ≤ 1024 chars (compress under 500); supporting directories `references/`, `scripts/`, `assets/`, `evals/`. Pi ignores unknown frontmatter fields, so the profile reports them as suggestions, not failures.
- **generic**: only verified common rules for SKILL.md-based skills. `name` and `description` required; no invented limits. Use when the target host is unknown or unverified, and state the assumption in the report.

## Conformance language

**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY** are RFC 2119. Hard requirements for host constraints and safety boundaries; guidance for strong defaults that still need judgment.

## Selecting and applying

1. Default to `pi`. Override with `--host generic` or `--profile <path>`.
2. The profile's frontmatter limits decide which lengths fail vs. warn. A field outside the allowed set is reported per the profile's `unknown_fields` policy (`suggest` by default).
3. When porting to an unlisted host, write a profile JSON before authoring; do not guess limits in prose.

## Writing a new profile

The schema is closed: unknown keys at any level are rejected so silent misconfiguration cannot happen. Top-level keys:

```text
schema_version            must be 1
profile                   string id used in reports
profile_description       one-line provenance of the rules
frontmatter               {required: [...], allowed: [...]}   (required ⊆ allowed)
name                      {pattern: regex, max_length: int|null}
description               {max_length: int|null, warn_above: int|null}
supporting_directories    plain directory names, e.g. references, scripts
ignored_paths             fnmatch patterns; trailing / ignores a directory at any depth
checks                    {forbidden_headings: bool, unknown_fields: ignore|suggest|fail}
```

Only include rules verified against that host's documentation or observed behavior; a profile must never encode assumptions. Ship it beside the skill's own assets when a bundle targets a new host.

## Naming rules

Folder names and `name` SHOULD be lowercase kebab-case (`project-sprint-planning`, not `ProjectSprintPlanning` or `project_sprint_planning`). `name` SHOULD match the folder; Pi permits a mismatch for shared skill directories.

## Frontmatter specification

Minimal viable frontmatter:

```yaml
---
name: your-skill-name
description: "What it does. Use when the user asks to [tasks or phrases]."
---
```

- `description` is the semantic index and selection contract: what it does, when to use it, trigger phrases, artifact types. Vague, literary, promotional, tutorial-length, or injection-shaped descriptions MUST NOT ship.
- Quote descriptions by default; plain YAML scalars break on `: ` and ` #`.
- Optional fields per host. Pi: `license`, `compatibility` (environment requirements, ≤ 500 chars), `metadata` (neutral key-value), `allowed-tools` (space-delimited tool list), `disable-model-invocation: true` (user-invoked only).
- Frontmatter loads earlier and more broadly than the body; treat it as high-sensitivity text. No executable code, no hidden injection, no bloat.

## Composability

A skill MUST NOT assume it is the only capability present. Scope to a clear domain, avoid conflicting global instructions, and leave unrelated host abilities alone.

## Portability

Avoid product marketing, UI-specific instructions, and vendor naming unless the skill is explicitly host-tied. Keep skills usable across agent surfaces; keep host-specific assumptions in `compatibility` or the profile.
