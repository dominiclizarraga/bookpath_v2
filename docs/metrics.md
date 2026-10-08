# Retrieval metrics

Compare retrieval methods on the same learning-goal queries, relevance labels,
and candidate books. Add one row per evaluated method or configuration.
This is the results table for the first benchmark and future dashboard.

## Results

| Method | nDCG@5 | Recall@10 | MRR | Precision@5 |
| --- | ---: | ---: | ---: | ---: |
| _No evaluated methods yet_ | — | — | — | — |

Replace the placeholder when the first method has been evaluated. A dash means
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

1. A versioned set of query texts and query IDs.
2. Reviewed relevance grades for query–book pairs.
3. Ranked book IDs from each method and one shared metric scorer.

For every result row, record the evaluation-set version, catalog checksum,
query count, text selection, method configuration, seed where applicable,
code commit, and run date in accompanying run notes. Give configurations
distinct method names, such as `tfidf_toc_v1` and `tfidf_toc_features_v1`;
these are naming examples, not implemented or measured methods.

No benchmark scores or metric-calculation code have been produced yet.
