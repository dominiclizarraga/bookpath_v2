# Retrieval metrics

Compare retrieval methods on the same learning-goal queries, relevance labels,
and candidate books. Add one row per evaluated method or configuration.
This is the results table for the first benchmark and future dashboard.

## Results

| Method | nDCG@5 | Recall@10 | MRR | Precision@5 |
| --- | ---: | ---: | ---: | ---: |
| Baseline 0: TF-IDF + cosine similarity | — | — | — | — |

Fill the row when independent relevance labels have been supplied. A dash means
**not measured**, rather than a score of zero. Store scores between 0 and 1,
shown to four decimal places. Higher is better for all four metrics.

## What each column measures

Calculate each metric per query, then average across the same fixed queries,
giving every query equal weight.

| Metric | Full name | Question it answers |
| --- | --- | --- |
| nDCG@5 | Normalized Discounted Cumulative Gain at 5 | Are the most useful books near the top of the first five results? It gives partial credit for relevance and more weight to earlier ranks. |
| Recall@10 | Recall at 10 | What fraction of the books labeled relevant for this query appear in the first ten results? |
| MRR | Mean Reciprocal Rank | How soon does the first relevant book appear? A first relevant result at rank 1 earns 1; rank 2 earns 0.5; rank 5 earns 0.2. |
| Precision@5 | Precision at 5 | How many of the first five results are relevant? Three relevant books earn 3 / 5 = 0.6. |

The definitions follow [Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)
and [NIST's reciprocal-rank implementation](https://github.com/usnistgov/trec_eval/blob/main/m_recip_rank.c).

## Proposed scoring rules

These rules establish the benchmark contract before we implement the scorer.
The binary relevance threshold below is awaiting review.

- **Ranking unit:** one book per `parent_asin`. Aggregate document or chunk
  scores into a unique book ranking before measuring these metrics.
- **Labels:** use the scale proposed in `next_steps/ideas.md`: 0 = irrelevant,
  1 = somewhat relevant, 2 = relevant, 3 = excellent recommendation.
- **nDCG@5:** use all four grades. At rank `r`, gain is
  `(2 ** grade - 1) / log2(r + 1)`. Divide the sum for the first five results
  by the best possible sum from this query's labeled candidate books.
- **Binary relevance (proposed):** grades 2 and 3 count as relevant for
  Recall@10, MRR, and Precision@5. Grade 1 still contributes to nDCG@5.
- **Recall@10:** divide relevant books found in the first ten results by all
  books labeled relevant for that query, including those not retrieved.
- **MRR:** use the first relevant book in the complete returned book ranking;
  use zero when none is returned. This is MRR, with no rank cutoff. A run that
  only returns ten results would measure MRR@10 and must not silently use this
  column.
- **Precision@5:** always divide by five. Returning fewer than five books
  leaves empty recommendation slots that contribute no credit.
- **Query coverage:** every method must evaluate the same queries. A method
  returning no results receives zero for that query. Require at least one
  relevant labeled candidate per query before scoring this benchmark.

Unjudged books are not confirmed irrelevant. Establish a shared set of judgments
before scoring; Recall@10 describes recall against those judgments, not every
potentially useful book in the catalog. Keep a separate held-out query set for
the final comparison when development queries are used to tune methods.

## What we need to fill the table

These three ingredients follow Stanford's
[information retrieval evaluation framework](https://nlp.stanford.edu/IR-book/html/htmledition/information-retrieval-system-evaluation-1.html).

1. A versioned set of query texts and query IDs.
2. Reviewed relevance grades for query–book pairs.
3. Ranked book IDs from each method and one shared metric scorer.

The initial [30 draft Business & Money queries](../benchmarks/gold_v1/queries.json)
and [collaborative labeling workflow](../benchmarks/gold_v1/README.md) now include
the user's edits. They preserve the exact baseline 0 query. The
[TF-IDF candidate report](../benchmarks/gold_v1/tfidf_candidates.md) contains ten
books for each query, giving 300 review pairs. Additional candidate sources and
relevance labels are pending, so this is not yet a gold standard.
Start with the [50-pair labeling pilot](../benchmarks/gold_v1/README.md#your-next-task)
before completing the current 300-pair list.

For every result row, record the evaluation-set version, catalog checksum,
query count, text selection, method configuration, seed where applicable,
code commit, and run date in accompanying run notes. Give configurations
distinct method names, such as `tfidf_toc_v1` and `tfidf_toc_features_v1`;
these are naming examples, not implemented or measured methods.

## Baseline 0: first retrieval run

The first run uses TF-IDF with cosine similarity and the exact query:

> I want to know what is needed to start a online business, given that i  have a finance background

Its complete ranking covers **9,034 books**. Text is the saved TOC and selected
book-level document text, joined per book. Titles remain display metadata.
Scikit-learn's `TfidfVectorizer()` defaults are used unchanged: lowercase word
tokens of two or more characters, unigrams, no stop-word removal, smooth IDF,
and L2 normalization. No query rewrite, parameter tuning, or reranking was done.
The vocabulary and IDF weights are fitted on candidate books, then the query
is transformed with those same weights.

Cosine similarity determines the order; **it is not a relevance judgment or
one of the four quality metrics**. The first book has cosine similarity
**0.2618**, which does not mean it is 26.18% relevant. Metrics remain unmeasured
because the user explicitly chose to retain the cosine ranking and leave
quality metrics unmeasured for this exercise.

The input query and recorded run are in
[benchmarks/baseline_0](../benchmarks/baseline_0/). The full ranking is saved
locally at `data/evaluation/baseline_0/ranking.parquet`. Inspect the method,
top ten results, and reproducibility checks in
[notebook 06](../notebooks/06_tfidf_baseline_0.ipynb).

This single query is an initial development example, not a multi-query benchmark.
No quality-metric scores or metric-calculation code have been produced yet.

Method documentation: [TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
and [cosine similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html).
For precision and recall definitions, see Stanford's
[evaluation of unranked retrieval sets](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-sets-1.html).
All supporting links are collected in [references.md](references.md).
