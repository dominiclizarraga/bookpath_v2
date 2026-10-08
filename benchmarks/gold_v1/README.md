# Draft Business & Money evaluation set

`queries.json` contains **30 user-reviewed learning goals** for the saved Business &
Money catalog. The first is the exact baseline 0 query. The others cover
entrepreneurship, marketing and sales, management, finance, economics and
strategy, and careers and people. These are proposed scenarios, not evidence
of the distribution of real user requests.

**This is not a gold-standard set yet.** The user has edited the goals and
success criteria, but no relevance labels have been assigned. Baseline 0's
query and ranking stay fixed.

## Inspect the TF-IDF candidates

Run `uv run python -m bookpath.candidates` to create a new local candidate run.
It uses the exact `query` text for retrieval; `background` and `success_criterion`
remain judgment context. An existing run is protected from overwrite.

- [tfidf_candidates.md](tfidf_candidates.md) lists the first ten books for each
  of the 30 queries: **300 query–book pairs**, covering **242 distinct books**.
- [tfidf_candidates.json](tfidf_candidates.json) records the query snapshot,
  candidate IDs, ranks, scores, input checksums, and code checksums.
- [Notebook 07](../../notebooks/07_tfidf_candidates_review.ipynb) lets the user
  select a query and book, then inspect the raw description/features and
  prepared TOC. It can hide ranks and scores for judgment.

The complete 30-query rankings contain **271,020 rows** and remain local at
`data/evaluation/gold_v1_tfidf/rankings.parquet`. The first query reproduces the
original baseline 0 ranking exactly. No additional-source candidates have
been added, and no grades have been assigned.

## Work together in small batches

### Your next task

Start with **50 query–book pairs**, rather than all 300 at once. In notebook 07,
use `query_number` 1, 7, 11, 16, and 24 to sample different learning goals. Set
`show_rank_and_scores = False` before judging; inspect the TOC and description
against each query's background and success criterion.

For each candidate, send the query ID, `parent_asin`, grade, and a brief reason:

```text
online_business_finance_001 | 1683509854 | 2 | Practical startup guidance; limited detail on operations.
```

That line illustrates the format, not an assigned label. Use **0 = irrelevant,
1 = somewhat relevant, 2 = relevant, 3 = excellent**. Say `uncertain` if the
available evidence is insufficient. Grade the same book again if it appears
for another query; its usefulness depends on that query's goal and background.
The notebook currently previews evidence and does not save grades.

After this pilot, check the rubric together and label the remaining candidates.
The current 300 pairs are a starting pool from TF-IDF only. Independently found
books and later methods can expand the pool; all compared methods must use the
same version of judgments. This follows Stanford's
[pooling approach](https://nlp.stanford.edu/IR-book/html/htmledition/assessing-relevance-1.html).

### Full workflow

1. **Review the queries.** The user edits unrealistic goals or backgrounds.
   Each query has a short success criterion to guide consistent labeling.
2. **Pilot five queries.** Check the grading rubric on a small batch before
   preparing candidates for all 30.
3. **Prepare a candidate pool per query.** Start with the first ten TF-IDF books
   and up to five additional books found independently through catalog keyword
   search, categories, or books the user already knows. Deduplicate the pool
   by `parent_asin`, preserving different parent records in the actual ranking.
   These searches discover labeling candidates; they do not tune baseline 0.
4. **Review books without scores or rank order.** Show the query, title, book ID,
   TOC, and available description/features. Summaries must remain grounded in
   those source fields, with full text available. Missing evidence is visible.
5. **The user assigns final grades.** Use 0 = irrelevant, 1 = somewhat relevant,
   2 = relevant, 3 = excellent. The grade is for this query and background.
   Allow a short reason and an explicit skip/uncertain choice. Unreviewed or
   uncertain items remain unlabeled; never turn them into grade 0 automatically.
6. **Freeze and measure.** Version the reviewed queries, pool, labels, and binary
   relevance threshold before calculating metrics. Preserve the original cosine
   ranking and record the evaluation-set version with every method's scores.

At most 15 books per query means up to 75 judgments in the five-query pilot,
then up to 450 for all 30. Overlap between candidate sources can reduce the work.
A confirmed equivalent edition can help the reviewer, but labels must not be
copied to another record solely because its title matches.

## Comparing future methods

When another method retrieves previously unjudged candidates, review those books
and create a new pool/label version. Recalculate every compared method against
that same version. Incomplete judgments limit the interpretation of Recall@10:
it measures recovery of known relevant books, not all relevant books in the
catalog. Record judgment coverage alongside the four requested metrics.

A grade belongs to the **query–book pair**, regardless of how the book was found.
Grade 3 means the book meets the query's excellent-match criteria; it does not
mean it is the only acceptable book or the winner of one method. Several books
can receive 3. If a new method finds another excellent book, add that book's
judgment to the shared pool and compare both methods again. Do not lower the
old book's grade merely because a new book was discovered. If evidence or the
rubric warrants revising a grade, version that change and rescore all methods.

Use some queries for development and reserve others for the final comparison
before using metric feedback to choose settings. The baseline 0 query belongs
to development because its results have already been inspected. The split is
not assigned yet; review query diversity before freezing it.

This workflow uses **pooling**, a standard way to collect relevance judgments
without reviewing every item in a large catalog. See
[Introduction to Information Retrieval: assessing relevance](https://nlp.stanford.edu/IR-book/html/htmledition/assessing-relevance-1.html).
Stanford's [test-collection discussion](https://nlp.stanford.edu/IR-book/html/htmledition/standard-test-collections-1.html)
provides context for incomplete judgments. The full project source index is in
[references.md](../../docs/references.md).

TF-IDF candidate collection and a read-only review notebook are implemented.
Additional candidate sources and label-entry/export controls remain pending.
