# Skills Reference Guide for Agents

Reading router: pick the focused reference that matches the task branch. Host rules outrank every reference; verify format limits, discovery behavior, and tool names against the host profile or host documentation.

## Routing by task

- **Creating or substantially restructuring a skill:** read [trigger-and-body-design.md](trigger-and-body-design.md), then [workflow-resource-graph.md](workflow-resource-graph.md) and [supporting-files.md](supporting-files.md); finish with [packaging-and-lifecycle.md](packaging-and-lifecycle.md).
- **Choosing where a new skill lives:** [destination-scopes.md](destination-scopes.md).
- **Fixing triggering:** the description and trigger-boundary rules in [trigger-and-body-design.md](trigger-and-body-design.md), plus the non-trigger cases in [testing-and-evaluation.md](testing-and-evaluation.md).
- **Choosing or questioning host limits:** [host-profiles.md](host-profiles.md).
- **Designing stages, handoffs, or the file graph:** [workflow-resource-graph.md](workflow-resource-graph.md).
- **Splitting material into references/scripts/assets/evals:** [supporting-files.md](supporting-files.md).
- **Debugging execution or building evaluations:** [testing-and-evaluation.md](testing-and-evaluation.md).
- **Destructive scope, secrets, or provenance doubts:** [safety-and-recovery.md](safety-and-recovery.md).
- **Packaging, publishing, versioning, rollback:** [packaging-and-lifecycle.md](packaging-and-lifecycle.md).

## Legacy section map

Earlier revisions of this guide carried numbered sections 1–22 in one file. They moved as follows, with no topic dropped:

| Legacy section | Now in |
|---|---|
| 1 What a skill is; 2 Why skills exist | trigger-and-body-design.md |
| 3 Conformance language | host-profiles.md |
| 4.1 Progressive disclosure; 4.5 Determinism; 4.6 Deliberate context | supporting-files.md |
| 4.2 Explicit triggering | trigger-and-body-design.md |
| 4.3 Composability; 4.4 Portability | host-profiles.md |
| 4.7 Proportionate failure behaviour | safety-and-recovery.md |
| 5 Skill anatomy; 12 Scripts; 13 References; 14 Assets; 21 Skeleton | supporting-files.md |
| 6 Naming rules; 7 Frontmatter specification | host-profiles.md |
| 8 Writing descriptions; 9 The body; 16 Anti-patterns | trigger-and-body-design.md |
| 10 Authoring procedure; 11 Instruction writing rules; 15 High value patterns | workflow-resource-graph.md |
| 17 Testing strategy; 18 Practical testing method; 19 Troubleshooting | testing-and-evaluation.md |
| 20 Packaging guidance; 22 Final review | packaging-and-lifecycle.md |
