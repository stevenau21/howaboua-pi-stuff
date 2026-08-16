#!/usr/bin/env python3
"""Structural, prompt-efficiency, and resource-graph checks for a skill directory.

Traverses local links and path mentions from SKILL.md to verify every bundled
resource is reachable, inside the skill root, correctly cased, acyclic, and
covered by the selected host profile. Never executes bundled scripts or fetches
external URLs.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath

FORBIDDEN_HEADINGS = re.compile(
    r"^#{1,6}\s+(purpose|when to use|do not use when|activation|triggers?)\b",
    re.I | re.M,
)
FIELD_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")
DESCRIPTION_HIGH_END = 500
DESCRIPTION_LIMIT = 1024
NAME_LIMIT = 64

# Host profile contract (closed schema; unknown keys are rejected).
PROFILE_SCHEMA_VERSION = 1
PROFILE_ROOT_KEYS = {
    "schema_version",
    "profile",
    "profile_description",
    "frontmatter",
    "name",
    "description",
    "supporting_directories",
    "ignored_paths",
    "checks",
}
PROFILE_FRONTMATTER_KEYS = {"required", "allowed"}
PROFILE_NAME_KEYS = {"pattern", "max_length"}
PROFILE_DESCRIPTION_KEYS = {"max_length", "warn_above"}
PROFILE_CHECK_KEYS = {"forbidden_headings", "unknown_fields"}
PROFILE_CHECK_UNKNOWN_VALUES = {"ignore", "suggest", "fail"}

DEFAULT_PROFILE = "pi"
MENTION_DIRS_DEFAULT = ("references", "scripts", "assets", "evals")
SCANNABLE_SUFFIXES = {".md", ".py", ".json", ".txt", ".yaml", ".yml", ".toml", ".sh", ".mjs", ".js", ".ts"}
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class ProfileError(ValueError):
    """Raised when a host profile file violates the closed schema."""


def split_frontmatter(text: str) -> tuple[list[tuple[int, str]], str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening YAML frontmatter delimiter")

    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing exact closing YAML frontmatter delimiter") from exc

    return list(enumerate(lines[1:end], start=2)), "\n".join(lines[end + 1 :]).lstrip("\n")


def parse_quoted_scalar(value: str, line_number: int) -> str:
    quote = value[0]
    if len(value) < 2 or not value.endswith(quote):
        raise ValueError(f"unterminated quoted frontmatter value at line {line_number}")

    inner = value[1:-1]
    if quote == "'":
        result: list[str] = []
        index = 0
        while index < len(inner):
            if inner[index] != "'":
                result.append(inner[index])
                index += 1
                continue
            if index + 1 >= len(inner) or inner[index + 1] != "'":
                raise ValueError(f"unescaped quote in frontmatter value at line {line_number}")
            result.append("'")
            index += 2
        return "".join(result)

    escaped = False
    for char in inner:
        if char == '"' and not escaped:
            raise ValueError(f"unescaped quote in frontmatter value at line {line_number}")
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    if escaped:
        raise ValueError(f"unfinished escape in frontmatter value at line {line_number}")
    return inner


def parse_scalar(value: str, line_number: int) -> str:
    if not value:
        return ""
    if value[0] in "\"'":
        return parse_quoted_scalar(value, line_number)
    if ": " in value or " #" in value:
        raise ValueError(
            f"frontmatter value at line {line_number} contains a plain-scalar trap; quote it"
        )
    return value


def parse_frontmatter(lines: list[tuple[int, str]]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line_number, line in lines:
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "\t")):
            continue
        match = FIELD_RE.fullmatch(line)
        if not match:
            raise ValueError(f"malformed top-level frontmatter at line {line_number}")
        key, raw_value = match.groups()
        if key in fields:
            raise ValueError(f"duplicate frontmatter field `{key}` at line {line_number}")
        fields[key] = (
            parse_scalar(raw_value or "", line_number)
            if key in {"name", "description"}
            else (raw_value or "")
        )
    return fields


def has_files(directory: Path) -> bool:
    return directory.is_dir() and any(path.is_file() for path in directory.rglob("*"))


def strip_fenced_code(text: str) -> str:
    """Remove fenced blocks before checking Markdown structure."""
    visible: list[str] = []
    fence_char = ""
    fence_length = 0

    for line in text.splitlines():
        marker = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if not fence_char:
            if marker:
                fence_char = marker.group(1)[0]
                fence_length = len(marker.group(1))
            else:
                visible.append(line)
            continue

        if re.fullmatch(
            rf"[ \t]{{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*", line
        ):
            fence_char = ""
            fence_length = 0

    return "\n".join(visible)


def visible_lines(text: str) -> list[tuple[int, str]]:
    """Return (1-based line number, line) pairs outside fenced code blocks."""
    lines = strip_fenced_code(text).splitlines()
    return list(enumerate(lines, start=1))


# --- Host profiles -----------------------------------------------------------


def _require_keys(data: dict, required: set[str], where: str) -> None:
    """Closed-schema check: every key is required and no unknown key is allowed."""
    missing = sorted(required - set(data))
    if missing:
        raise ProfileError(f"missing profile key(s) in {where}: {', '.join(missing)}")
    unknown = sorted(set(data) - required)
    if unknown:
        raise ProfileError(f"unknown profile key(s) in {where}: {', '.join(unknown)}")


def _require_str_list(value: object, where: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ProfileError(f"{where} must be a non-empty list of strings")
    if any(not isinstance(item, str) or not item for item in value):
        raise ProfileError(f"{where} must contain only non-empty strings")
    if len(set(value)) != len(value):
        raise ProfileError(f"{where} contains duplicate entries")
    return value


def load_profile(path: Path) -> dict:
    """Load and validate a host profile against the closed schema."""
    label = path.name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"cannot read host profile {label}: {exc}") from exc

    if not isinstance(data, dict):
        raise ProfileError(f"host profile {label} must be a JSON object")
    _require_keys(data, PROFILE_ROOT_KEYS, f"host profile {label}")

    if data["schema_version"] != PROFILE_SCHEMA_VERSION:
        raise ProfileError(
            f"host profile {label} schema_version must be {PROFILE_SCHEMA_VERSION}"
        )
    if not isinstance(data["profile"], str) or not data["profile"]:
        raise ProfileError(f"host profile {label} profile must be a non-empty string")
    if not isinstance(data["profile_description"], str):
        raise ProfileError(f"host profile {label} profile_description must be a string")

    frontmatter = data["frontmatter"]
    if not isinstance(frontmatter, dict):
        raise ProfileError(f"host profile {label} frontmatter must be an object")
    _require_keys(frontmatter, PROFILE_FRONTMATTER_KEYS, f"host profile {label} frontmatter")
    _require_str_list(frontmatter["required"], f"host profile {label} frontmatter.required")
    _require_str_list(frontmatter["allowed"], f"host profile {label} frontmatter.allowed")
    missing_allowed = sorted(set(frontmatter["required"]) - set(frontmatter["allowed"]))
    if missing_allowed:
        raise ProfileError(
            f"host profile {label} frontmatter.required entries not allowed: {', '.join(missing_allowed)}"
        )

    for section, keys, limit_keys in (
        ("name", PROFILE_NAME_KEYS, ("max_length",)),
        ("description", PROFILE_DESCRIPTION_KEYS, ("max_length", "warn_above")),
    ):
        value = data[section]
        if not isinstance(value, dict):
            raise ProfileError(f"host profile {label} {section} must be an object")
        _require_keys(value, keys, f"host profile {label} {section}")
        for limit_key in limit_keys:
            limit = value[limit_key]
            if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
                raise ProfileError(
                    f"host profile {label} {section}.{limit_key} must be a positive integer or null"
                )
    try:
        re.compile(data["name"]["pattern"])
    except re.error as exc:
        raise ProfileError(f"host profile {label} name.pattern is not a valid regex: {exc}") from exc

    _require_str_list(
        data["supporting_directories"], f"host profile {label} supporting_directories"
    )
    for directory in data["supporting_directories"]:
        if PurePosixPath(directory).name != directory:
            raise ProfileError(
                f"host profile {label} supporting_directories entries must be plain names: {directory}"
            )
    if any(not isinstance(item, str) or not item for item in data["ignored_paths"]):
        raise ProfileError(f"host profile {label} ignored_paths must contain non-empty strings")

    checks = data["checks"]
    if not isinstance(checks, dict):
        raise ProfileError(f"host profile {label} checks must be an object")
    _require_keys(checks, PROFILE_CHECK_KEYS, f"host profile {label} checks")
    if not isinstance(checks["forbidden_headings"], bool):
        raise ProfileError(f"host profile {label} checks.forbidden_headings must be a boolean")
    if checks["unknown_fields"] not in PROFILE_CHECK_UNKNOWN_VALUES:
        raise ProfileError(
            f"host profile {label} checks.unknown_fields must be one of: "
            + ", ".join(sorted(PROFILE_CHECK_UNKNOWN_VALUES))
        )
    return data


# --- Resource graph ----------------------------------------------------------


def normalize_relpath(target: str) -> str:
    """Normalize a slash-separated relative target (no scheme, no fragment)."""
    return posixpath.normpath(target.replace("\\", "/"))


def link_targets(line: str, mention_re: re.Pattern[str]) -> set[str]:
    """Extract candidate local reference targets from one visible line."""
    targets: set[str] = set()
    for match in re.finditer(r"(?<!\!)\[[^\]]*\]\(\s*([^)\s]+)\s*\)", line):
        targets.add(match.group(1))
    for match in re.finditer(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)", line):
        targets.add(match.group(1))
    for match in mention_re.finditer(line):
        target = match.group(1).rstrip(".,;:!?\"')")
        if target:
            targets.add(target)
    return targets


def is_ignored(relpath: str, patterns: list[str]) -> bool:
    posix = relpath.replace("\\", "/")
    segments = posix.split("/")
    for pattern in patterns:
        normalized = pattern.replace("\\", "/")
        if normalized.endswith("/"):
            # Directory pattern: ignore the named directory at any depth.
            wanted = [seg for seg in normalized.strip("/").split("/") if seg]
            count = len(wanted)
            if any(segments[i : i + count] == wanted for i in range(len(segments) - count + 1)):
                return True
        elif fnmatch.fnmatch(posix, normalized):
            return True
    return False


def build_inventory(root: Path, profile: dict) -> dict[str, str]:
    """Map casefolded relative paths to actual relative paths for entries under root."""
    inventory: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        if not (path.is_file() or path.is_dir()):
            continue
        relpath = path.relative_to(root).as_posix()
        if is_ignored(relpath, profile["ignored_paths"]):
            continue
        inventory[relpath.casefold()] = relpath
    return inventory


def classify_node(relpath: str, profile: dict) -> str:
    top = relpath.split("/", 1)[0]
    if relpath == "SKILL.md":
        return "root"
    if top in profile["supporting_directories"]:
        return top.rstrip("s") if top.endswith("s") else top
    return "other"


def extract_edges(
    source_relpath: str,
    text: str,
    root: Path,
    inventory: dict[str, str],
    mention_re: re.Pattern[str],
) -> tuple[list[dict], list[dict], list[str]]:
    """Extract graph edges, diagnostics, and external URLs from one file's text."""
    edges: list[dict] = []
    diagnostics: list[dict] = []
    external: list[str] = []

    source_is_root = source_relpath == "SKILL.md"
    for line_number, line in visible_lines(text):
        for raw in sorted(link_targets(line, mention_re)):
            target = raw.split("#", 1)[0].rstrip("/")
            fragment_only = target == ""
            if fragment_only:
                continue
            if PurePosixPath(target).is_absolute() or re.match(r"^[A-Za-z]:", target):
                diagnostics.append(
                    {
                        "file": source_relpath,
                        "line": line_number,
                        "message": f"absolute path escapes the skill root: {raw}",
                    }
                )
                continue
            if SCHEME_RE.match(target):
                external.append(target)
                continue

            joined = posixpath.normpath(
                posixpath.join(posixpath.dirname(source_relpath), target.replace("\\", "/"))
            )
            if joined.startswith("../"):
                diagnostics.append(
                    {
                        "file": source_relpath,
                        "line": line_number,
                        "message": f"path escapes the skill root: {raw}",
                    }
                )
                continue

            actual = inventory.get(joined.casefold())
            if actual is None:
                from_link = bool(re.search(r"(?<!\!)\[[^\]]*\]\(\s*[^)\s]*" + re.escape(raw.split("#", 1)[0]) + r"[^)]*\)", line) or re.search(r"^\s{0,3}\[[^\]]+\]:\s*" + re.escape(raw), line))
                if source_is_root or from_link:
                    diagnostics.append(
                        {
                            "file": source_relpath,
                            "line": line_number,
                            "message": f"dangling reference: {raw} resolves to missing {joined}",
                        }
                    )
                continue
            if actual != joined:
                diagnostics.append(
                    {
                        "file": source_relpath,
                        "line": line_number,
                        "message": f"case mismatch: {raw} should be {actual}",
                    }
                )
            if (root / actual).is_dir():
                diagnostics.append(
                    {
                        "file": source_relpath,
                        "line": line_number,
                        "message": f"reference target is a directory, expected a file: {raw}",
                    }
                )
                continue
            if not source_is_root and actual == "SKILL.md" and not re.search(
                r"\[[^\]]*\]\(\s*[^)\s]*" + re.escape(raw.split("#", 1)[0]), line
            ):
                continue  # prose mention of SKILL.md inside a reference: not a back-edge
            edges.append(
                {"source": source_relpath, "target": actual, "line": line_number}
            )
    return edges, diagnostics, external


def find_cycles(nodes: dict[str, list[dict]]) -> list[list[str]]:
    """Return every cycle in the link graph, each as a full path ending where it started."""
    cycles: list[list[str]] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for edge in nodes.get(node, []):
            target = edge["target"]
            if state.get(target) == 1:
                start = stack.index(target)
                cycles.append(stack[start:] + [target])
            elif state.get(target, 0) == 0:
                visit(target)
        stack.pop()
        state[node] = 2

    for node in sorted(nodes):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run structural, prompt-efficiency, and resource-graph checks on a skill."
    )
    parser.add_argument("skill", help="Path to SKILL.md or a skill directory")
    parser.add_argument(
        "--host",
        choices=sorted(path.stem for path in (Path(__file__).resolve().parent.parent / "assets" / "host-profiles").glob("*.json")),
        default=DEFAULT_PROFILE,
        help=f"Host profile governing limits and rules (default: {DEFAULT_PROFILE})",
    )
    parser.add_argument(
        "--profile",
        help="Explicit host profile JSON path; overrides --host",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings (e.g. orphaned supporting files) as failures",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="Output format (default: text)"
    )
    args = parser.parse_args()

    target = Path(args.skill).expanduser()
    if target.is_dir():
        target = target / "SKILL.md"
    target = target.resolve()
    root = target.parent

    profile: dict = {}
    profile_error = ""
    profile_path = Path(args.profile).expanduser() if args.profile else None
    if profile_path is None:
        profile_path = Path(__file__).resolve().parent.parent / "assets" / "host-profiles" / f"{args.host}.json"
    try:
        profile = load_profile(profile_path)
    except ProfileError as exc:
        profile_error = str(exc)

    issues: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []
    fields: dict[str, str] = {}
    body = ""
    parsed = False

    if profile_error:
        issues.append(f"host profile is invalid: {profile_error}")
    if target.name != "SKILL.md" or not target.is_file():
        issues.append(f"missing SKILL.md: {target}")
    elif not profile_error:
        try:
            text = target.read_text(encoding="utf-8")
            frontmatter, body = split_frontmatter(text)
            fields = parse_frontmatter(frontmatter)
            parsed = True
        except (OSError, UnicodeError, ValueError) as exc:
            issues.append(str(exc))

    name = fields.get("name", "")
    description = fields.get("description", "")

    if parsed and not profile_error:
        name_rule = profile["name"]
        frontmatter_rule = profile["frontmatter"]

        for required in frontmatter_rule["required"]:
            if required not in fields or not fields[required]:
                issues.append(f"frontmatter missing {required}")

        unknown_fields_policy = profile["checks"]["unknown_fields"]
        for key in fields:
            if key not in frontmatter_rule["allowed"]:
                message = f"frontmatter field `{key}` is not in the {profile['profile']} profile's allowed set"
                if unknown_fields_policy == "fail":
                    issues.append(message)
                elif unknown_fields_policy == "suggest":
                    suggestions.append(message)

        if name:
            if name_rule["max_length"] is not None and len(name) > name_rule["max_length"]:
                issues.append(
                    f"name too long: {len(name)} chars > {profile['profile']} limit of {name_rule['max_length']}"
                )
            if name_rule["pattern"] and not re.fullmatch(name_rule["pattern"], name):
                issues.append(
                    f"name does not match the {profile['profile']} pattern {name_rule['pattern']}: {name}"
                )

        if description:
            if not re.search(r"\buse (?:when|for)\b", description, re.I):
                warnings.append("description may not clearly say when to use the skill")
            desc_rule = profile["description"]
            if desc_rule["max_length"] is not None and len(description) > desc_rule["max_length"]:
                issues.append(
                    f"description too long: {len(description)} chars > {profile['profile']} limit of {desc_rule['max_length']}"
                )
            elif (
                desc_rule["warn_above"] is not None and len(description) > desc_rule["warn_above"]
            ):
                warnings.append(
                    f"description is long for agent-facing retrieval: {len(description)} chars; "
                    "compress job, triggers, artifacts, outcomes, and boundaries"
                )

    checks_rule = profile.get("checks", {}) if profile else {}
    if checks_rule.get("forbidden_headings", True):
        if FORBIDDEN_HEADINGS.search(strip_fenced_code(body)):
            issues.append("body contains job/selection headings; keep those semantics in description")

    # --- Resource graph ------------------------------------------------------

    nodes: list[dict] = []
    edges: list[dict] = []
    external_links: list[str] = []
    graph_issues: list[dict] = []
    orphan_warnings: list[dict] = []
    inventory: dict[str, str] = {}

    if not profile_error and target.is_file() and target.name == "SKILL.md":
        inventory = build_inventory(root, profile)
        mention_re = re.compile(
            r"(?<![\w./\\-])((?:"
            + "|".join(re.escape(part) for part in profile["supporting_directories"])
            + r")(?:[/\\][\w.-]+)+)"
        )
        scanned: dict[str, str] = {}
        for fold, relpath in inventory.items():
            path = root / relpath
            if path.suffix.lower() not in SCANNABLE_SUFFIXES:
                continue
            try:
                scanned[fold] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue

        adjacency: dict[str, list[dict]] = {}
        seen_edges: set[tuple[str, str]] = set()
        for source_fold, text_content in scanned.items():
            source_relpath = inventory[source_fold]
            source_edges, diagnostics, external = extract_edges(
                source_relpath, text_content, root, inventory, mention_re
            )
            graph_issues.extend(diagnostics)
            external_links.extend(external)
            for edge in source_edges:
                adjacency.setdefault(edge["source"], []).append(edge)
                key = (edge["source"], edge["target"])
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append(edge)

        for cycle in find_cycles(adjacency):
            graph_issues.append(
                {
                    "file": cycle[0],
                    "line": 0,
                    "message": "reference cycle: " + " -> ".join(cycle),
                }
            )

        reachable: set[str] = {"SKILL.md"}
        stack = ["SKILL.md"]
        while stack:
            current = stack.pop()
            for edge in adjacency.get(current, []):
                if edge["target"] not in reachable:
                    reachable.add(edge["target"])
                    stack.append(edge["target"])

        supporting = {
            fold: relpath
            for fold, relpath in inventory.items()
            if relpath.split("/", 1)[0] in profile["supporting_directories"]
            and (root / relpath).is_file()
        }
        for fold, relpath in sorted(supporting.items()):
            if relpath not in reachable:
                orphan_warnings.append(
                    {
                        "file": relpath,
                        "line": 0,
                        "message": f"orphaned supporting file: {relpath} is not reachable from SKILL.md",
                    }
                )

        node_set = {"SKILL.md"} | {edge["source"] for edge in edges} | {
            edge["target"] for edge in edges
        } | {entry["file"] for entry in orphan_warnings}
        nodes = [
            {"path": relpath, "kind": classify_node(relpath, profile)}
            for relpath in sorted(node_set)
        ]
        external_links = sorted(set(external_links))

    issues.extend(
        f"{entry['file']}:{entry['line']}: {entry['message']}" for entry in graph_issues
    )
    warnings.extend(
        f"{entry['file']}:{entry['line']}: {entry['message']}" for entry in orphan_warnings
    )

    if not profile_error:
        if not has_files(root / "references"):
            suggestions.append(
                "no references found; consider whether detailed guidance, examples, or edge cases would help"
            )
        if not has_files(root / "scripts"):
            suggestions.append(
                "no scripts found; consider whether deterministic validation or transformation would help"
            )

    failed = bool(issues) or (args.strict and bool(warnings))

    if args.format == "json":
        print(
            json.dumps(
                {
                    "profile": profile.get("profile", args.host),
                    "strict": args.strict,
                    "skill": str(target),
                    "summary": {
                        "nodes": len(nodes),
                        "edges": len(edges),
                        "external_links": len(external_links),
                        "issues": len(issues),
                        "warnings": len(warnings),
                        "suggestions": len(suggestions),
                        "failed": failed,
                    },
                    "nodes": nodes,
                    "edges": edges,
                    "external_links": external_links,
                    "issues": issues,
                    "warnings": warnings,
                    "suggestions": suggestions,
                },
                indent=2,
            )
        )
    else:
        print("# Skill Efficiency Check\n")
        print(f"skill: {target}")
        print(f"profile: {profile.get('profile', args.host)}")
        print(f"description_chars: {len(description)}")
        print(f"body_chars: {len(body)}")
        print(f"body_lines: {len(body.splitlines())}")
        print(f"graph_nodes: {len(nodes)}")
        print(f"graph_edges: {len(edges)}")
        print(f"external_links: {len(external_links)}")
        print("\n## Issues")
        print("- none" if not issues else "\n".join(f"- {item}" for item in issues))
        print("\n## Warnings")
        print("- none" if not warnings else "\n".join(f"- {item}" for item in warnings))
        print("\n## Suggestions")
        print("- none" if not suggestions else "\n".join(f"- {item}" for item in suggestions))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
