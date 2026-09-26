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

In `data/raw/books.parquet`, `toc_entries` is a **DataFrame column**. One cell
contains an array of TOC dictionaries for that book. It sits alongside
`raw_toc_json` and `openlibrary_raw_edition_json`. After decoding those two JSON
columns, we found no key named `toc_entries` inside them in any of the 9,034
records. To access it, use the DataFrame column `books["toc_entries"]`.
Inside the decoded `openlibrary_raw_edition_json`, the TOC key is named
`table_of_contents`. The next section shows the columns and their contents.

- `raw_toc_shape` is `list[dict]` for 9,030 records and `list[string]` for 4.
- `raw_toc_item_count` and `toc_entry_count` differ for 17 records.

The 4 books with plain-string raw TOC items are different from the 17 books
with count differences, giving 21 books to inspect. For every row, the number
of dictionaries in its `toc_entries` cell equals its stored `toc_entry_count`.

### Deeper TOC exploration (2026-09-23)

This section describes the **9,034 book records saved in
`data/raw/books.parquet`**. The notebook
[02_toc_eda.ipynb](../notebooks/02_toc_eda.ipynb) reads that local file into a
Pandas DataFrame named `books`. Each row is an Amazon parent-book record,
identified by `parent_asin`. Different rows can refer to the same Open Library
edition.

A **TOC entry** is one item in a book's table of contents, such as a chapter,
preface, or volume. One book row can contain many TOC entries. These are all
five TOC-specific columns plus the full Open Library source column:

The examples in the table all refer to *Never Split the Difference*, the row
with `parent_asin == "0062407805"`. Keys listed for a TOC item refer to this
book's first item; other books can have different raw keys.

| Column in `books` | Data structure in one cell | Keys or value in this example |
| --- | --- | --- |
| `openlibrary_raw_edition_json` | JSON string → dictionary after `json.loads()` | The key `table_of_contents` holds a list of 14 items. Other keys describe the book. |
| `raw_toc_json` | JSON string → list after `json.loads()` | First item's keys: `label`, `title`, `subtitle`, `level`, `pagenum`, `type`. |
| `raw_toc_item_count` | String containing a count | `"14"`; no nested keys. |
| `raw_toc_shape` | String describing the raw list | `"list[dict]"`; no nested keys. This means a list of dictionaries. |
| `toc_entries` | NumPy array containing dictionaries | Each dictionary's keys: `text`, `source_key`, `sequence`, `level`, `page`. |
| `toc_entry_count` | String containing a count | `"14"`; no nested keys. |

The arrow in the table means that `json.loads()` reads the stored JSON string
and returns a Python dictionary or list. It does not change the stored column.

**Real row: `parent_asin == "0062407805"`**, *Never Split the Difference*.
Below, the JSON-string columns are shown **after decoding** so their contents
are readable. Only the first TOC item is shown; both TOC lists contain 14 items.
The full Open Library record also contains other book information, omitted here.

```text
books: one row for parent_asin "0062407805"
├── openlibrary_raw_edition_json  (JSON string; decoded view below)
│   └── table_of_contents        (list of 14 original items)
│       └── item 1: {"label": "Chapter 1", "title": "The New Rules",
│                    "subtitle": "How to Become the Smartest Person in Any Room",
│                    "level": 0, "pagenum": "1", "type": {"key": "/type/toc_item"}}
├── raw_toc_json                 (JSON string; decoded list of 14 original items)
│   └── item 1: {"label": "Chapter 1", "title": "The New Rules",
│                "subtitle": "How to Become the Smartest Person in Any Room",
│                "level": 0, "pagenum": "1", "type": {"key": "/type/toc_item"}}
├── raw_toc_item_count: "14"
├── raw_toc_shape: "list[dict]"
├── toc_entries                  (array of 14 parsed dictionaries)
│   └── item 1: {"text": "The New Rules", "source_key": "title",
│                "sequence": "1", "level": "0", "page": "1"}
└── toc_entry_count: "14"
```

The six names at the same indentation are **six separate DataFrame columns**.
Only `table_of_contents` is a nested key inside the decoded Open Library JSON.

Here, **raw** means the original Open Library TOC. **Parsed** means its items
have already been arranged into those five keys. Both versions were present in
the downloaded dataset; this notebook compares them. Parsed does not mean fully
cleaned or checked for mistakes.

**Example 1: the same chapter before and after parsing**

In `books`, find the row with `parent_asin == "0062407805"`. Its book-title
column, `title`, contains *Never Split the Difference: Negotiating As If Your
Life Depended On It*.

Run this from the repository root, or use the `books` DataFrame already loaded
in the notebook. All Python examples below keep this same `selected_book`:

```python
import json
from bookpath.local_data import read_books_from_parquet

books = read_books_from_parquet("data/raw/books.parquet")
selected_book = books.loc[books["parent_asin"] == "0062407805"].iloc[0]
```

The first item in that row's decoded `raw_toc_json` is shown below. Here,
`title` is a key **inside the chapter's dictionary**. Its value is the chapter
title, `"The New Rules"`; it is separate from the DataFrame's book-title column.

```python
raw_entry = json.loads(selected_book["raw_toc_json"])[0]
raw_entry
```

Result, shown as JSON:

```json
{
  "label": "Chapter 1",
  "title": "The New Rules",
  "subtitle": "How to Become the Smartest Person in Any Room",
  "level": 0,
  "pagenum": "1",
  "type": {"key": "/type/toc_item"}
}
```

In this one chapter, `label` supplies `"Chapter 1"`, `title` supplies
`"The New Rules"`, and `subtitle` supplies the longer explanation of the
chapter. `pagenum` gives the page label, `level` records its depth in the TOC,
and `type` is Open Library's record-type information.

The **first dictionary in `toc_entries` for the same book** is:

```python
parsed_entry = selected_book["toc_entries"][0]
parsed_entry
```

Result, shown as JSON:

```json
{
  "text": "The New Rules",
  "source_key": "title",
  "sequence": "1",
  "level": "0",
  "page": "1"
}
```

These are the five parsed fields and how they relate to the raw example above:

| Parsed field | Value for this chapter | Meaning |
| --- | --- | --- |
| `text` | `"The New Rules"` | The text taken from the raw item's `title`. |
| `source_key` | `"title"` | The name of the raw key that supplied `text`. |
| `sequence` | `"1"` | Position 1 in this book's parsed TOC list. |
| `level` | `"0"` | The raw level `0`, stored here as a string. |
| `page` | `"1"` | The page label taken from raw `pagenum`. |

The chapter title stays `"The New Rules"` in both the raw and parsed versions.
The raw dictionary also contains `label` and `subtitle`. The parsed dictionary
does not contain those two keys or their text for this chapter. We can still
read them from the original dictionary in `raw_toc_json`.

**Check `title`, `value`, and `label` in the same chapter**

Keep using `raw_entry`, which came from the `raw_toc_json` column for
*Never Split the Difference*. Here is what each lookup returns:

```python
raw_entry.get("title")   # "The New Rules"
raw_entry.get("value")   # None: this item has no key named "value"
raw_entry.get("label")   # "Chapter 1"
```

`get()` reads a dictionary key and returns `None` if that key is absent.
In this example, we can confirm the absence directly:

```python
"value" in raw_entry     # False
```

None of this book's 14 raw TOC items has a `value` key. We cannot show a real
`value` example from this book. Some other books use that key to hold TOC text.

The observed selection across the dataset is: take text from `title` if it is
present and not blank; otherwise try `value`, then `label`. For our example
chapter, `title` already contains `"The New Rules"`, so that is the text kept:

```python
parsed_entry["source_key"]   # "title"
parsed_entry["text"]         # "The New Rules"
```

The label `"Chapter 1"` is not added to that text. Across all books, 140,446
parsed entries use `title`, 759 use `value`, and 161 use `label`. Another 129
raw items are plain strings rather than dictionaries, so their parsed entries
have no source-key name. These totals describe other books too; they do not
mean our example book uses every format.

**What did we compare, and what matched?**

First, we checked whether the two columns storing the Open Library TOC agree.
For our example book, the comparison is:

```python
raw_toc = json.loads(selected_book["raw_toc_json"])
edition = json.loads(selected_book["openlibrary_raw_edition_json"])
raw_toc == edition["table_of_contents"]   # True
```

This is also `True` for every other row: both places store the same TOC list.

The `==` comparison checks the decoded lists, including their order and the
keys and values in each dictionary. It checks more than the number of items.
The `# True` above is only a comment showing the observed result. In a notebook,
the expression displays `True` or `False`; it does not stop execution on a
difference. To make a difference stop execution, use:

```python
assert raw_toc == edition["table_of_contents"], "The two saved TOC copies differ."
```

This example checks one book. Section 2 of `02_toc_eda.ipynb` performs the same
comparison for every row and reports the match count: **9,034 of 9,034**.
That confirms the two saved copies agree; it does not check them against the
published book.

Second, we checked what text from `raw_toc_json` appears in `toc_entries`.
For the first chapter of our example book:

```python
raw_entry["title"] == parsed_entry["text"]   # True: both are "The New Rules"
```

Our example book has 14 items in each column. Across all 9,034 rows, there are
141,513 items in decoded `raw_toc_json` and 141,495 entries in `toc_entries`.
The difference is 18 raw items, spread across 17 books, without text to keep.
For example, one such item contains `"value": ""` (an empty string).

When we compare the remaining text, ignoring spaces at its beginning or end,
every chosen text matches and stays in the same order. Levels and pages match
too, allowing for numbers stored as strings: raw `0` becomes parsed `"0"`.
The recorded `source_key` also agrees with the key that supplied the text.

`sequence` counts positions in `toc_entries`, starting at 1. If an empty raw
item was left out, the later entries are numbered without a gap. Our example
book has no omitted items; this numbering difference applies to other books.

Matching chapter text does not mean the whole dictionaries are identical.
The next example shows additional text in `raw_toc_json` that is absent from
`toc_entries`. Nor does matching our two stored versions establish whether
Open Library's TOC matches the contents of the published book.

**What would we miss by reading only `toc_entries`?**

For the same first chapter of *Never Split the Difference*, reading only the
`toc_entries` column gives us the chapter title but no chapter subtitle:

```python
selected_book["toc_entries"][0]["text"]          # "The New Rules"
selected_book["toc_entries"][0].get("label")    # None: key absent
selected_book["toc_entries"][0].get("subtitle") # None: key absent
```

Reading the **`raw_toc_json` column** for that same chapter gives us the
chapter number and the explanatory subtitle as well:

```python
raw_entry = json.loads(selected_book["raw_toc_json"])[0]
raw_entry["title"]      # "The New Rules"
raw_entry["label"]      # "Chapter 1"
raw_entry["subtitle"]   # "How to Become the Smartest Person in Any Room"
```

So, if we build recommendation text using only `toc_entries`, this chapter
contributes `"The New Rules"`. It will not contribute `"Chapter 1"` or
`"How to Become the Smartest Person in Any Room"`, because neither appears in
that parsed entry. **That is what "miss those details" means.** Both strings
are still saved in `raw_toc_json`; they have not disappeared from the dataset.
We have not yet decided whether to include them in recommendation text.

Here is the broader count of extra keys in decoded `raw_toc_json`. The example
values still refer to our same book's first chapter; the two count columns
cover the entire dataset.

| Key in a raw TOC item | Value in our example chapter | Items with this key, all books | Books with this key |
| --- | --- | ---: | ---: |
| `label` | `"Chapter 1"` | 3,801 | 204 |
| `subtitle` | `"How to Become the Smartest Person in Any Room"` | 16 | 2 |
| `authors` | Key absent in this chapter | 6 | 5 |
| `description` | Key absent in this chapter | 1 | 1 |
| `class` | Key absent in this chapter | 69 | 5 |

The dictionaries in `toc_entries` have none of these key names. However, a
raw key's value can sometimes be copied into `text`: that is what happens
when another book uses `label` as its text source. We need to inspect the
values as well as the key names before deciding what information was omitted.

**Which entries need a closer look?**

Percentages below use all 141,495 parsed entries.

| Observation | Entries | Books affected, where checked |
| --- | ---: | ---: |
| Missing page | 135,121 (95.50%) | — |
| Missing level | 10,370 (7.33%) | — |
| Text containing only digits, such as `"15"` | 435 | 44 |
| Text that looks like it contains HTML tags | 21 | 4 |
| Exact text repeated within a book, counting every occurrence | 2,875 | 167 |
| Repeated after case/whitespace normalization, counting every occurrence | 2,916 | 177 |

No parsed entry has missing or blank text. Repetition does not automatically
mean an error: a heading such as `"To Learn More"` can appear after several
chapters. The repeat counts include every occurrence, including the first one.
The second repeat check treats `"Introduction"` and `" introduction "` as equal
for counting, without changing the saved text.

`level` describes depth in the TOC: for example, a section might sit below a
chapter. Only 97 books have more than one recorded level, and 680 have none.
There are 21 jumps of more than one level between neighboring entries, such as
`0` followed by `2`. We need the surrounding entries to understand these jumps.

Of 6,374 entries with a page, 155 use something other than plain digits, such as
`"ix"`, `"1-1"`, or `"1.10"`. Those can be valid page labels. Likewise,
`"v. 2. The wheels of commerce"` names a volume, not a chapter. Our search for
volume labels finds 170 entries in 47 books, but the limited English patterns
may miss other ways of writing them.

An entry has a median length of 30 characters; the longest has 1,474. Adding up
each book's entry lengths gives a median of 410 characters and a maximum of
17,370. These counts exclude any separators we might add when joining entries
and do not tell us how many tokens a language model would use.

**Can more TOC text be hidden elsewhere?**

Yes. The Amazon JSON has no dedicated TOC key in our search, but some descriptions
contain actual chapter lists. For example, `0142000280` (*Getting Things Done*)
has `"Table of Contents"` followed by entries such as `"Chapter 1 - A New Practice
for a New Reality"`.

Searching for phrases such as "table of contents" finds 23 Amazon descriptions,
22 Amazon feature lists, and 2 Open Library notes. Some only say that the book
includes a TOC. A book can appear in more than one group, and our phrase search
can miss chapter lists written differently. These matches need manual inspection.

The two EDA notebooks only inspect and count the data. They do not remove or
merge entries or create text features. The separate first implementation below
builds candidate text features. The saved raw Parquet remains unchanged.

### TOC preprocessing strategy: first implementation

Implemented in [src/bookpath/toc.py](../src/bookpath/toc.py). See the before/after
examples in [03_toc_features_preview.ipynb](../notebooks/03_toc_features_preview.ipynb).

**What:** Build a new, separate set of TOC entries from the local
`raw_toc_json` column. It contains the same TOC as
`openlibrary_raw_edition_json["table_of_contents"]` after decoding, and keeps
more detail than `toc_entries`. Use `toc_entries` to check the new extraction.

- **Main text:** Read nonblank `title`, otherwise `value`, otherwise `label`;
  also handle items that are already plain strings. Include a chapter's
  nonblank `subtitle` when it adds text not already in the main text. These
  are keys inside `raw_toc_json`, not the DataFrame's book-title/subtitle columns.
- **Context:** Keep raw `label`, `level`, `class`, and `pagenum` for chapter
  numbering, nesting, and page references. Keep `authors` and `description`
  for review before deciding whether they belong in recommendation text.
- **Traceability:** Keep `parent_asin`, `ol_edition_key`, the original item
  position, and the key used for its text. Keep each full source item in
  `raw_item_json`, including unknown keys. Flag empty, numeric-only, and
  repeated items for review. Possible extra TOCs in Amazon descriptions remain
  a separate investigation; this implementation does not merge them.

**Why:** The counts (140,446 from `title`, 759 from `value`, 161 from `label`,
129 plain strings) tell us which formats to support. They do not tell us which
text produces better recommendations. Starting from `raw_toc_json` lets us
retain useful chapter subtitles such as "How to Become the Smartest Person in
Any Room", which the current `toc_entries` leaves out.

**Expected result:** A separate local processed dataset with fuller chapter
text, useful context, and a way to trace every entry back to the saved source.
The raw file stays unchanged. Compare retrieval using the existing TOC text
against text with the additional chapter information under an agreed evaluation
plan before adopting it for recommendations.

**First saved result:** `data/processed/toc_features.parquet`, created with:

```sh
uv run python -m bookpath.toc
```

This file has **141,513 rows**, one per raw item across all 9,034 books, including
18 items flagged `missing_text`. The 141,495 nonmissing `base_text` values
reproduce the existing `toc_entries` text in order. All 16 chapter subtitles
add text in this snapshot. There are 435 `numeric_only_text` flags and 2,916
`repeated_text` flags; flagged rows are retained. Repeat comparison ignores case
and repeated whitespace within the same book and marks every occurrence.

For the first chapter of *Never Split the Difference* (`0062407805`):

| Output column | Actual value |
| --- | --- |
| `base_text` | `The New Rules` |
| `chapter_subtitle` | `How to Become the Smartest Person in Any Room` |
| `feature_text` | `The New Rules: How to Become the Smartest Person in Any Room` |
| `text_source` | `title` |
| `raw_position` | `1` |
| `subtitle_added` | `True` |

`feature_text` trims outer whitespace and adds the subtitle with `: ` between
the two parts. It avoids adding a subtitle whose whole word sequence already
appears in the main text, ignoring case and punctuation. This is a simple text
comparison, not a test of equivalent meaning. If only a chapter subtitle has
text, it can supply `feature_text` on its own. Neither behavior changes the raw
source item.

Context columns include `book_title`, `label`, `level`, `page`, `entry_class`,
`authors_json`, and `description_json`. They are retained for inspection and
are not automatically joined into `feature_text`. The saved file also records
`feature_version = "toc-v1"` and `source_sha256`, the raw file checksum.
Existing outputs are protected from overwrite; choose another `--output` path
to save a later experiment. No fitted preprocessing or embeddings are involved.

## Evaluation design before choosing retrieval features

The EDA notebooks remain descriptive. A separate candidate TOC feature dataset
now exists for inspection. No train/test split, fitted transformation,
resampling, embedding model, or ranking evaluation has been created. Its text
rules still need evaluation before being adopted for recommendations.

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
the deduplication unit, missing descriptions, and TOC text/metadata quality. No
automatic deletion or filling rule has been chosen.

Any later refresh should create a new raw file or record its date, query, row
count, and checksum before replacing this snapshot.
