# Data

## Raw books snapshot

The first raw snapshot is stored locally at `data/raw/books.parquet`. The
`data/` directory is ignored by Git, so the file is not committed. It is a
source artifact: do not edit it during preprocessing.

It was downloaded on 2026-09-22 with:

```sh
uv run python -m bookpath.bigquery --max-rows 10000 --output data/raw/books.parquet
```

The command requested at most 10,000 records and returned 9,034. It saved the
file, then read it back locally. The snapshot has 38 columns, is 92,373,274
bytes, and has SHA-256:

```text
4acf6979b15215c28f2a45a1488ace4d749e2573f0fa4a0110e2933dd0194dd8
```

Read it without querying BigQuery:

```python
from bookpath.local_data import read_books_from_parquet

books = read_books_from_parquet("data/raw/books.parquet")
```

The download is ordered by `parent_asin`; it is not a random sample. Results
below describe this snapshot only and should not be treated as population-wide
statistics about all books.

## First EDA: data-quality baseline

This EDA is descriptive only. No rows, columns, or values were changed.
Reproduce the checks in
[01_raw_books_eda.ipynb](../notebooks/01_raw_books_eda.ipynb), using the project's
`.venv` kernel and **Restart Kernel → Run All**. The notebook reads only local
Parquet and checks its checksum again at the end. Rerun it to refresh any saved
outputs.

### Unit and identifiers

- The raw row is currently treated as one Amazon parent-book record.
- `parent_asin` is complete and unique: 9,034 non-missing values and no
  duplicates. It is the current row-level identifier.
- `canonical_isbn_13` has 38 duplicate groups containing 77 rows: 39 rows are
  additional copies beyond the first occurrence. The largest group has 3 rows.
- `ol_edition_key` has 150 duplicate groups containing 307 rows: 157 rows are
  additional copies beyond the first occurrence. The largest group has 4 rows.

These secondary-key duplicates are not automatically errors. They may represent
different Amazon parent records matched to the same ISBN or OpenLibrary edition.
Do not deduplicate by title, ISBN, or edition key until we inspect those groups
and decide whether the recommendation unit is a parent book, an edition, or a
work.

### Missingness and basic coverage

| Column | Missing records | Share |
| --- | ---: | ---: |
| `ol_subtitle` | 2,088 | 23.1% |
| `subtitle` | 928 | 10.3% |
| `store` | 12 | 0.1% |
| `ol_publish_date` | 3 | <0.1% |
| `main_category` | 2 | <0.1% |

All other columns have no null values in this Parquet snapshot. `title` and
`ol_title` have no blank strings. This measures presence only; it does not
establish that the text is useful or correctly matched.

Null checks alone missed empty collections. In particular, `description` contains
lists, and **1,028 records (11.38%) have an empty description list**. The earlier
string-based check did not establish description coverage.

| Collection column | Empty lists/arrays | Share of raw records |
| --- | ---: | ---: |
| `ol_isbn_10` | 2,422 | 26.81% |
| `ol_isbn_13` | 1,233 | 13.65% |
| `description` | 1,028 | 11.38% |
| `ol_publishers` | 792 | 8.77% |
| `features` | 43 | 0.48% |
| `ol_work_keys` | 2 | 0.02% |

The checked `categories`, `isbn_aliases`, `matched_isbn_aliases`, and
`toc_entries` collections have no empty lists/arrays. Nonempty collections can
still contain missing or unhelpful elements; this check does not inspect every
element's content.

### Candidate subtitle feature for a later phase

`subtitle` is the Amazon source field. `ol_subtitle` is the `subtitle` field
from the matched Open Library **edition**: Open Library defines a work as a
collection of editions, and lists `subtitle` as an edition field. See
[Open Library's work-and-edition field guide](https://openlibrary.org/about/work_edition).

Of the 928 records with a missing Amazon `subtitle`:

| Amazon subtitle status | Records |
| --- | ---: |
| Missing Amazon subtitle, present `ol_subtitle` | 695 (74.9%) |
| Missing Amazon subtitle, missing `ol_subtitle` | 233 (25.1%) |

The 695 Open Library subtitles should not automatically be copied into the raw
Amazon `subtitle` column. A simple lowercase-and-punctuation-normalized check
found that 581 of their texts already appear inside the Amazon `title`; adding
them again would duplicate words in a future text feature. The other 114 are
not contained by that check, but still require review because the matched
edition can have different metadata or wording.

For future feature engineering, record this as a **candidate row-level subtitle
imputation rule** for a derived field such as `subtitle_for_text`:

1. Use the Amazon `subtitle` when present.
2. Otherwise, use `ol_subtitle` only when it is present and its normalized text
   is not already contained in the Amazon `title`.
3. Otherwise, leave `subtitle_for_text` missing and use the title alone.

Keep the original `subtitle` and `ol_subtitle` unchanged, and add an explicit
provenance label such as `subtitle_source` (`amazon`, `openlibrary`, or
`missing`). This rule uses fields from the same record and learns no dataset-wide
parameter, but it still needs comparison against a title-only baseline in the
agreed retrieval evaluation. No fallback, imputation, copying, oversampling, or
row removal has been applied yet.

### Open Library text fields to explore later

Inside `openlibrary_raw_edition_json`, 10 of the 9,034 records contain a nonempty
`work_title` (a cataloging title for the underlying work), and 8,489 contain
nonempty `subjects` (topic headings such as `Economic history.`). Neither is a
separate DataFrame column. The other 545 edition records lack the `subjects`
key; this does not establish whether their linked works have subjects. See
[Open Library's field guide](https://openlibrary.org/about/work_edition).

Both are candidates for later exploration with text embeddings or small language
models, not selected features yet. No extraction or raw-data changes were made.

### Numeric parsing diagnostics

The following fields are stored as strings in the raw file, but every value
parsed successfully as a number during this EDA:

| Field | Median | 99th percentile | Maximum |
| --- | ---: | ---: | ---: |
| `average_rating` | 4.4 | 5.0 | 5.0 |
| `rating_number` | 26 | 4,856.5 | 90,755 |
| `raw_toc_item_count` | 12 | 86.7 | 581 |
| `toc_entry_count` | 12 | 86.7 | 581 |

`rating_number` is strongly right-skewed in this snapshot. That is a descriptive
observation, not a reason to remove or resample records.

### Category and source coverage

Every raw record carries both `Books` and `Business & Money` in `categories`.
This artifact therefore has business-related category coverage; it does not
establish coverage of arbitrary learning goals. All records are labeled
`exact_isbn_alias` in `match_type`; this label does not independently validate
the matching process.

Examples of category membership are `Management & Leadership` (2,374 records,
26.28%) and `Economics` (963, 10.66%). The notebook counts each category once per
parent record. Categories can overlap, so percentages need not sum to 100%.
No supervised target is defined, so these counts are not a class-imbalance
assessment and do not justify resampling.

### Table-of-contents structure

- `raw_toc_shape` is `list[dict]` for 9,030 records and `list[string]` for 4.
- `raw_toc_item_count` and `toc_entry_count` differ for 17 records.

The two groups do not overlap: there are 21 distinct flagged records. The actual
length of `toc_entries` agrees with `toc_entry_count` for every record. The
raw-versus-parsed count differences therefore need investigation of the upstream
parsing, rather than an assumption that the saved Parquet lost entries.

## Stop here: evaluation design before further development

This pass stops at descriptive inspection. No processed dataset, train/test
split, fitted transformation, imputation, feature selection, resampling,
chunking, embeddings, or model evaluation has been created.

The full saved catalog has been inspected, so it is development evidence, not
an untouched test set. Before using these observations to choose modeling or
preprocessing strategies, define the evaluation task and what is held out:
queries, users, books, or related works/editions. A retrieval candidate catalog
and held-out evaluation queries have different roles.

For unseen-book evaluation, related editions and chunks must respect the chosen
book/work grouping. Fit learned preprocessing using training data only and use
development/validation data for tuning. See
[scikit-learn's leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).

Unresolved questions for a later step include numeric types and validation,
the deduplication unit, missing descriptions, and TOC parsing differences. No
automatic deletion or filling rule has been chosen.

Any later refresh should create a new raw file or record its date, query, row
count, and checksum before replacing this snapshot.
