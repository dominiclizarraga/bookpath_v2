---
name: data-science-review
description: Review preprocessing, exploratory analysis, experiments, and conclusions for statistical correctness. Use when assessing sampling, deduplication, imbalance, uncertainty, or statistical claims.
---

# Data Science Review

Read applicable AGENTS.md instructions. Establish the question, target population,
unit of analysis, sampling/selection process, and evidence available for the review.

Check where relevant:
- Missingness, filtering, and coverage before/after cleaning; preserve raw evidence.
- Duplicate records versus related entities; do not treat editions or chunks as
  independent books, or remove records solely because titles match.
- Meaningful denominators, weighting, and distributions; imbalance alone does not
  justify resampling, and outliers alone do not justify removal.
- Evaluation leakage, test assumptions, effect sizes, uncertainty, multiple
  comparisons, and conclusions that overreach observational evidence.
- Consistent experiment comparisons; resampling and uncertainty estimates should
  respect the independent unit and the evaluation design.

Use available local data and report its scope. Do not infer full-dataset statistics
from a small convenience sample or treat unavailable evidence as a passed check.
Do not change data, thresholds, or analysis code unless requested.

Report findings by impact with file/line or artifact, evidence, consequence for the
conclusion, and a suggested correction. Separate descriptive results from inference,
and state assumptions and unresolved uncertainty.
