# BookPath

BookPath recommends a learning path through books based on a user's goal and existing knowledge.

## Problem

People often know what they want to learn but not:
- which book to start with
- what level is appropriate
- what to read next

## Current hypothesis

Semantic retrieval + metadata + learning-level information
can produce better learning paths than semantic similarity alone.

[Next steps for this version](https://drive.google.com/file/d/1bQ2rPnr4xgu1v_5GnS9fvN_v7HOH1KKY/view?usp=drive_link)

## Tests

Install the project dependencies with `uv sync`, then run:

```sh
uv run pytest
```

Tests use invented book records and temporary files. BigQuery subprocess calls
are mocked; tests do not need Google credentials or submit real queries.

## Local book data

The data-access pieces currently have separate responsibilities:

- `bigquery.py`: `main()` downloads up to 10 records by default and saves a raw sample. If
  the destination already exists, it skips the query and leaves the file unchanged.
  Calling `load_books()` directly still queries BigQuery every time.
- `local_data.py`: saves DataFrames as Parquet files and reads them back without
  contacting BigQuery. It does not clean or otherwise preprocess the data.

From the repository root, download the initial sample:

```sh
uv run python -m bookpath.bigquery
```

The first run requires your BigQuery CLI credentials and `BOOKPATH_GCP_PROJECT`,
`BOOKPATH_BQ_DATASET`, `BOOKPATH_BQ_TABLE`, and `BOOKPATH_BQ_LOCATION` in the
environment or `.env`. It saves `data/raw/books_sample.parquet`, reads it back,
and prints the row count and column names. Subsequent runs stop before loading
cloud configuration or querying BigQuery if that path exists.

For later exploration or preprocessing, read the local sample:

```python
from bookpath.local_data import read_books_from_parquet

books = read_books_from_parquet("data/raw/books_sample.parquet")
```

Reading never downloads data. A missing file raises `FileNotFoundError`.
Saving writes a temporary file first and moves it into place only after the
write succeeds. Existing files are protected unless `overwrite=True` is given,
and failed writes leave the previous file intact. Book identifiers must be columns;
the DataFrame index is not saved. Local `data/` files are ignored by Git.

To download up to 10,000 records to a separate file:

```sh
uv run python -m bookpath.bigquery --max-rows 10000 --output data/raw/books.parquet
```

Use both flags together to choose the row count and its destination. The command
leaves the sample untouched and skips BigQuery if the chosen output already exists.
Read the larger dataset locally with:

```python
books = read_books_from_parquet("data/raw/books.parquet")
```

Both downloads are ordered by `parent_asin`, not randomly sampled. They are not
necessarily complete or representative datasets. SQL `LIMIT` and the CLI row
limit bound returned records, not the bytes scanned or query cost. Preprocessing
should read raw local data and write a separate processed Parquet file.

## Exploratory data analysis

Run `uv sync`, then open
[notebooks/01_raw_books_eda.ipynb](notebooks/01_raw_books_eda.ipynb) in VS Code.
Choose **Select Kernel → Python Environments → .venv/bin/python**, then
**Restart Kernel → Run All**. The notebook can run from the repository root
or the `notebooks/` directory. It requires the existing `data/raw/books.parquet`.

The notebook checks nulls, empty collections, repeated identifiers, numeric
parsing, category coverage, and TOC counts. It ends
before preprocessing and evaluation decisions. Findings and the stopping point
are recorded in [docs/data.md](docs/data.md).

Continue with [notebooks/02_toc_eda.ipynb](notebooks/02_toc_eda.ipynb) for deeper
TOC exploration: source preservation, additional raw fields, ordering, hierarchy,
pages, repeated text, lengths, and possible contents lists inside descriptions.
Run it from the same `.venv` kernel; it reads the existing local Parquet.

## TOC feature preview

Create the first processed TOC file from the saved raw snapshot:

```sh
uv run python -m bookpath.toc
```

This writes `data/processed/toc_features.parquet`, with one row per raw TOC item.
It keeps source fields and review flags, and builds `feature_text` from chapter
text plus a chapter subtitle when it adds information. It never downloads data
or overwrites an existing output. Use `--input` and `--output` for other paths.

Open [03_toc_features_preview.ipynb](notebooks/03_toc_features_preview.ipynb) with
the `.venv` kernel and **Run All** to see *Never Split the Difference* before
and after this step. The preview reads the saved processed file and verifies it
against the raw snapshot. The feature has not been evaluated for retrieval yet.

`build_toc_features(books)` in `src/bookpath/toc.py` builds the inspection table
in memory. `prepare_toc_features(input_path, output_path)` handles local file
reading and saving. The raw data remains unchanged; `data/` is not committed.

Notebook dependencies are development dependencies: `ipykernel` runs Python
cells, `matplotlib` draws plots, and `nbclient` supports execution checks from
a fresh kernel. Rerun the notebook to refresh any saved outputs.
