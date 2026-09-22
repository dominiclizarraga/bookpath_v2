---
name: software-review
description: Review Python changes for correctness, software conventions, maintainability, and test quality. Use for software or code-review requests, not statistical or model-quality assessments.
---

# Software Review

Read applicable AGENTS.md instructions. Inspect the requested changes, relevant
callers, and tests. If no scope is given, start with the working-tree changes.

Check where relevant:
- Clear names, cohesive responsibilities, and explicit dependencies.
- Input/output contracts, error handling, resource cleanup, and import side effects.
- File-write safety, configuration, dependency declarations, and lockfile consistency.
- Tests of observable behavior, failure cases, and isolated external boundaries.

Run focused local checks when useful. Do not contact live services for a review.
Treat line-count preferences as guidelines; identify practical consequences rather
than enforcing style mechanically. Do not introduce tooling or edit code unless requested.

Report concrete findings first, ordered by impact. Include file/line, evidence,
consequence, and a suggested correction. Separate bugs from optional conventions.
State checks performed and remaining uncertainty; if no issues are found, say so.
