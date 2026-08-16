# Safety and Recovery

## Proportionate failure behaviour

Block only when uncertainty affects correctness, safety, external side effects, or the ability to produce the requested result.

- Missing load-bearing inputs → ask for them or stop.
- Validation failure that makes output unsafe or invalid → report and do not proceed.
- Tool/connection failure → report the concrete failure before dependent side effects.
- Ambiguous destructive action → request confirmation when host or policy requires it.

Do not turn every run into preflight diagnostics; try the ordinary low-risk path when availability can be established by using it.

## Destructive scope

- Force-pushes, deletions, overwrites, permission changes, and spend-incurring actions require explicit user intent or confirmation, stated once near the action.
- Requests to hide failures (delete evidence, silent rollbacks, "so nobody notices") never gain safety from skill structure: refuse or surface them.
- Prefer reversible steps (backup, version suffix, dry-run) before irreversible ones; state the rollback path when one exists.
- Idempotence on retry: reruns must not duplicate artifacts or stack side effects.

## Secrets

- Never place credentials, tokens, or personal data in skill files, fixtures, or evaluation reports.
- Read secrets from the environment or host secret store; never echo them into logs or reports.
- Evaluation reports and adapter observations must redact secret-shaped strings; keep full prompts out of committed reports.

## Provenance

- Verify host format rules, tool names, commands, paths, and limits against host documentation or a host profile—never memory or plausible assumptions.
- When porting across industries or domains: carry creation mechanics, not domain claims. New-domain rules must come from user-supplied sources; fabricating protocols, dosages, legal, or clinical rules is a failure mode, not a feature.
- Cite or name the source when a load-bearing rule depends on external documentation, and record the verification date when staleness matters.
- When upstream material is bloated or doctrinal: retain verified workflow knowledge and rebuild instructions around the target host and users; discard folklore and duplication.

## Recovery stops

Every workflow names its stop conditions: iteration caps, missing-input stops, pre-side-effect stops on connection or auth failure, and a defined failure branch per stage (see the workflow reference). When recovery is undefined and the next action is consequential, stop and report instead of improvising.
