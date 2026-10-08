# Sources behind the project decisions

These references support the explanations in the notebooks and project docs.
They describe methods; they do not establish BookPath's recommendation quality.

## Relevance labels and evaluation

- [Stanford: information retrieval system evaluation](https://nlp.stanford.edu/IR-book/html/htmledition/information-retrieval-system-evaluation-1.html) explains why a test collection needs documents, information needs, and independent relevance judgments. Used in [metrics.md](metrics.md).
- [Stanford: assessing relevance](https://nlp.stanford.edu/IR-book/html/htmledition/assessing-relevance-1.html) explains human judgments and pooling candidates from multiple retrieval methods. Used in the [labeling workflow](../benchmarks/gold_v1/README.md) and [notebook 07](../notebooks/07_tfidf_candidates_review.ipynb).
- [Stanford: standard test collections](https://nlp.stanford.edu/IR-book/html/htmledition/standard-test-collections-1.html) describes pooled judgments and their incomplete coverage of large catalogs.
- [Stanford: evaluation of ranked retrieval results](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html) supports graded relevance, discounted gain, and precision at a cutoff. Used in [metrics.md](metrics.md).
- [Stanford: evaluation of unranked retrieval sets](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-sets-1.html) defines precision and recall.
- [NIST trec_eval: reciprocal rank](https://github.com/usnistgov/trec_eval/blob/main/m_recip_rank.c) implements the reciprocal rank of the first relevant result. Used in [metrics.md](metrics.md).

BookPath's 0–3 grading scale and proposed binary threshold of 2 are project
choices; the references do not prescribe this exact rubric. The current
TF-IDF-only candidate list needs additional candidate sources before a fair
comparison with later methods. Unjudged books are not confirmed irrelevant.

## TF-IDF baseline and reproducibility

- [scikit-learn: TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) documents the unchanged default settings used by baseline 0.
- [scikit-learn: cosine_similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html) defines the vector similarity used to rank books. It is not a human relevance label.
- [scikit-learn: data leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage) explains separating fitting from evaluation. The catalog and held-out evaluation queries have different roles; baseline 0 fits TF-IDF on the catalog and transforms queries afterward.

See [notebook 06](../notebooks/06_tfidf_baseline_0.ipynb) and
[data.md](data.md) for the saved input, configuration, and validation results.
The user also supplied *Natural Language Processing in Action*, chapters 2
(tokenization) and 3 (TF-IDF); the scikit-learn example appears on printed page
93 of the supplied TF-IDF excerpt. The supplied PDFs are not redistributed here.

## Missing data and source fields

- [Rubin (1976): Inference and missing data](https://doi.org/10.1093/biomet/63.3.581) is the original missing-data framework reference.
- [Sterne et al. (2009): Multiple imputation for missing data](https://pmc.ncbi.nlm.nih.gov/articles/PMC2714692/) explains the assumptions and why observed data alone cannot distinguish MAR from MNAR.
- [Open Library: works and editions](https://openlibrary.org/about/work_edition) describes work-level and edition-level metadata fields.

These support [data.md](data.md) and the missing-data discussion in
[notebook 01](../notebooks/01_raw_books_eda.ipynb) and
[notebook 02](../notebooks/02_toc_eda.ipynb). The user supplied Chip Huyen's
*Designing Machine Learning Systems*, chapter 5, “Handling Missing Values,”
page 124. Its MCAR, MAR, and MNAR concepts are documented as hypotheses, not
proven causes of missingness in this dataset.

## Automated code checks

- [uv: GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/) documents installing locked dependencies and running tests in CI.
- [actions/checkout](https://github.com/actions/checkout) checks out the committed source.
- [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv) installs uv and the selected Python version.

The [test workflow](../.github/workflows/tests.yml) runs offline tests on pushes
and pull requests. A green check verifies those tests, not recommendation quality.
