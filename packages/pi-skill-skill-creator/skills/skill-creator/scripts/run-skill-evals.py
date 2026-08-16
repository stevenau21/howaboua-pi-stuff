#!/usr/bin/env python3
"""Deterministic validation of skill evaluation fixtures, with optional live adapters.

Default mode checks the fixture schema offline and reports coverage; it never
invokes a model. With --adapter, an external harness executes each case and
returns one JSON observation per line; observations are matched structurally.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

CASES_SCHEMA_VERSION = 1
VALID_KINDS = {"trigger", "execution", "recovery", "portability"}
VALID_EXPECT_KEYS = {
    "activated",
    "artifacts_present",
    "artifacts_absent",
    "diagnostics_present",
    "diagnostics_absent",
    "forbidden_actions",
}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgho_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghu_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghs_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghr_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}"),
]


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


class FixtureError(ValueError):
    pass


def validate_fixtures(data: object, source: str) -> list[dict]:
    if not isinstance(data, dict):
        raise FixtureError(f"{source}: fixtures must be a JSON object")
    unknown = sorted(set(data) - {"schema_version", "cases"})
    if unknown:
        raise FixtureError(f"{source}: unknown key(s): {', '.join(unknown)}")
    if data.get("schema_version") != CASES_SCHEMA_VERSION:
        raise FixtureError(
            f"{source}: schema_version must be {CASES_SCHEMA_VERSION}"
        )
    cases = data["cases"]
    if not isinstance(cases, list) or not cases:
        raise FixtureError(f"{source}: cases must be a non-empty list")

    seen_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        where = f"{source}: case {index}"
        if not isinstance(case, dict):
            raise FixtureError(f"{where} must be an object")
        unknown = sorted(set(case) - {"id", "kind", "request", "expect"})
        if unknown:
            raise FixtureError(f"{where}: unknown key(s): {', '.join(unknown)}")
        for key in ("id", "kind", "request", "expect"):
            if key not in case:
                raise FixtureError(f"{where} missing `{key}`")
        case_id = case["id"]
        if not isinstance(case_id, str) or not ID_RE.fullmatch(case_id):
            raise FixtureError(f"{where}: id must be lowercase kebab-case: {case_id!r}")
        if case_id in seen_ids:
            raise FixtureError(f"{source}: duplicate case id: {case_id}")
        seen_ids.add(case_id)
        if case["kind"] not in VALID_KINDS:
            raise FixtureError(
                f"{case_id}: kind must be one of {', '.join(sorted(VALID_KINDS))}"
            )
        if not isinstance(case["request"], str) or not case["request"].strip():
            raise FixtureError(f"{case_id}: request must be a non-empty string")
        expect = case["expect"]
        if not isinstance(expect, dict) or not expect:
            raise FixtureError(f"{case_id}: expect must be a non-empty object")
        unknown = sorted(set(expect) - VALID_EXPECT_KEYS)
        if unknown:
            raise FixtureError(
                f"{case_id}: unknown expect key(s): {', '.join(unknown)}; "
                f"valid keys: {', '.join(sorted(VALID_EXPECT_KEYS))}"
            )
        if "activated" not in expect:
            raise FixtureError(f"{case_id}: expect must state `activated`")
        for key in ("artifacts_present", "artifacts_absent", "forbidden_actions"):
            if key in expect and (
                not isinstance(expect[key], list)
                or any(not isinstance(item, str) or not item for item in expect[key])
            ):
                raise FixtureError(f"{case_id}: expect.{key} must be a list of non-empty strings")
        for key in ("diagnostics_present", "diagnostics_absent"):
            if key in expect and (
                not isinstance(expect[key], list)
                or not expect[key]
                or any(not isinstance(item, str) or not item for item in expect[key])
            ):
                raise FixtureError(
                    f"{case_id}: expect.{key} must be a non-empty list of regex strings"
                )
        for key in ("diagnostics_present", "diagnostics_absent"):
            if key in expect:
                for pattern in expect[key]:
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        raise FixtureError(
                            f"{case_id}: expect.{key} entry is not a valid regex: {pattern} ({exc})"
                        ) from exc
    return cases


def run_adapter(
    command: str, case: dict, timeout: float
) -> tuple[dict | None, str]:
    """Run one adapter invocation; return (observation, failure reason)."""
    try:
        completed = subprocess.run(
            shlex.split(command),
            input=json.dumps(case),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"adapter timed out after {timeout:g}s"
    except OSError as exc:
        return None, f"adapter could not be executed: {exc}"

    if completed.returncode != 0:
        detail = redact(completed.stderr.strip() or completed.stdout.strip())
        return None, f"adapter exited with code {completed.returncode}: {detail}"

    line = completed.stdout.strip().splitlines()
    if not line:
        return None, "adapter produced no output"
    try:
        observation = json.loads(line[-1])
    except json.JSONDecodeError as exc:
        return None, f"adapter output is not valid JSON: {redact(line[-1])} ({exc})"
    if not isinstance(observation, dict):
        return None, "adapter output must be a JSON object"
    if observation.get("id") != case["id"]:
        return None, (
            f"adapter returned id {observation.get('id')!r}; expected {case['id']!r}"
        )
    return observation, ""


def match_observation(case: dict, observation: dict) -> list[str]:
    """Return structural mismatches between one case's expectations and observation."""
    failures: list[str] = []
    expect = case["expect"]
    case_id = case["id"]

    activated = observation.get("activated")
    if not isinstance(activated, bool):
        failures.append(f"{case_id}: observation `activated` must be a boolean")
    elif activated is not expect["activated"]:
        failures.append(
            f"{case_id}: expected activated={expect['activated']}, observed {activated}"
        )

    artifacts = observation.get("artifacts")
    if artifacts is None:
        artifacts = []
    if not isinstance(artifacts, list):
        failures.append(f"{case_id}: observation `artifacts` must be a list when present")
        artifacts = []
    for required in expect.get("artifacts_present", []):
        if required not in artifacts:
            failures.append(f"{case_id}: expected artifact present: {required}")
    for forbidden in expect.get("artifacts_absent", []):
        if forbidden in artifacts:
            failures.append(f"{case_id}: expected artifact absent: {forbidden}")

    diagnostics = " ".join(
        item if isinstance(item, str) else json.dumps(item)
        for item in (observation.get("diagnostics") or []) + (observation.get("errors") or [])
    )
    for pattern in expect.get("diagnostics_present", []):
        if not re.search(pattern, diagnostics, re.I):
            failures.append(
                f"{case_id}: expected diagnostics matching /{pattern}/; observed: {redact(diagnostics) or '(none)'}"
            )
    for pattern in expect.get("diagnostics_absent", []):
        if re.search(pattern, diagnostics, re.I):
            failures.append(
                f"{case_id}: expected no diagnostics matching /{pattern}/; observed: {redact(diagnostics)}"
            )

    actions = observation.get("actions")
    if actions is None:
        actions = []
    if not isinstance(actions, list):
        failures.append(f"{case_id}: observation `actions` must be a list when present")
        actions = []
    action_text = " ".join(item if isinstance(item, str) else json.dumps(item) for item in actions)
    for forbidden in expect.get("forbidden_actions", []):
        if forbidden.lower() in action_text.lower():
            failures.append(f"{case_id}: forbidden action observed: {forbidden}")

    return failures


def main() -> int:
    default_cases = Path(__file__).resolve().parent.parent / "evals" / "cases.json"
    parser = argparse.ArgumentParser(
        description="Validate skill evaluation fixtures; optionally run them via an adapter."
    )
    parser.add_argument(
        "--cases", default=str(default_cases), help=f"Path to cases JSON (default: {default_cases})"
    )
    parser.add_argument(
        "--adapter",
        help=(
            "Optional live adapter command. The runner sends one case JSON object on stdin "
            "and expects one normalized observation JSON object per line on stdout."
        ),
    )
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="Adapter timeout per case in seconds (default: 30)"
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="Output format (default: text)"
    )
    args = parser.parse_args()

    cases_path = Path(args.cases).expanduser()
    try:
        data = json.loads(cases_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"error: cannot read cases file {cases_path}: {exc}", file=sys.stderr)
        return 2

    try:
        cases = validate_fixtures(data, cases_path.name)
    except FixtureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    results: list[dict] = []
    if args.adapter:
        for case in cases:
            observation, failure = run_adapter(args.adapter, case, args.timeout)
            if observation is None:
                results.append(
                    {"id": case["id"], "status": "error", "failures": [f"{case['id']}: {failure}"]}
                )
                continue
            failures = match_observation(case, observation)
            results.append(
                {
                    "id": case["id"],
                    "status": "passed" if not failures else "failed",
                    **({} if not failures else {"failures": failures}),
                }
            )
    else:
        results = [
            {"id": case["id"], "status": "fixture-valid", "kind": case["kind"]}
            for case in cases
        ]

    failed = [entry for entry in results if entry["status"] in {"failed", "error"}]

    if args.format == "json":
        print(
            json.dumps(
                {
                    "cases": cases_path.name,
                    "adapter": args.adapter or None,
                    "summary": {
                        "total": len(results),
                        "passed": len(results) - len(failed),
                        "failed": len(failed),
                        "failed_run": bool(failed),
                    },
                    "results": results,
                },
                indent=2,
            )
        )
    else:
        mode = f"adapter: {args.adapter}" if args.adapter else "fixture validation only (no model)"
        print("# Skill Evals\n")
        print(f"cases: {cases_path}")
        print(f"mode: {mode}")
        print(f"total: {len(results)}  passed: {len(results) - len(failed)}  failed: {len(failed)}")
        print("\n## Results")
        for entry in results:
            print(f"- {entry['id']}: {entry['status']}")
            for failure in entry.get("failures", []):
                print(f"  - {redact(failure)}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
