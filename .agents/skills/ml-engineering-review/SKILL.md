---
name: ml-engineering-review
description: Review data and ML pipelines for reproducibility, leakage, feature consistency, and evaluation readiness. Use for ML engineering reviews; assess only stages relevant to the current task.
---

# ML Engineering Review

Read applicable AGENTS.md instructions and trace the requested pipeline stage's
inputs, transformations, outputs, and tests. Separate implemented behavior from plans.

Check where relevant:
- Explicit ingestion/refresh; local preprocessing must not silently query remote data.
- Complete, traceable datasets; preserved identifiers/schema; safe artifact writes.
- Recorded data/model/tokenizer versions, configuration, seeds, and cache identity.
- Consistent training/inference features and preprocessing fitted only on training data.
- Evaluation splits appropriate to the goal, including related editions and chunks.
- Suitable baselines and metrics; for retrieval, check relevance labels, candidate
  corpus, ranking unit, and aggregation from chunks to books.

Use local fixtures and existing artifacts. Do not download data, train models, call
providers, or modify code unless that work is requested. Do not require deployment
infrastructure for an exploratory stage.

Report findings by impact with file/line, evidence, failure scenario, and correction.
Distinguish confirmed failures from missing evidence and future improvements.
State verification limits; passing code tests alone does not establish model quality.
