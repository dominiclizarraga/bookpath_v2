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

- `bigquery.py`: `main()` calls `load_books()` to download a DataFrame into memory.
  Each invocation of that command sends a new query to BigQuery.
- `local_data.py`: saves DataFrames as Parquet files and reads them back without
  contacting BigQuery. It does not clean or otherwise preprocess the data.

Once a download has produced a `books` DataFrame, save it explicitly:

```python
from bookpath.local_data import save_books_to_parquet

save_books_to_parquet(books, "data/raw/books.parquet")
```

For later exploration or preprocessing, read the local file:

```python
from bookpath.local_data import read_books_from_parquet

books = read_books_from_parquet("data/raw/books.parquet")
```

Reading never downloads data. A missing file raises `FileNotFoundError`.
Saving writes a temporary file first and moves it into place only after the
write succeeds. Existing files are protected unless `overwrite=True` is given,
and failed writes leave the previous file intact. Book identifiers must be columns;
the DataFrame index is not saved. Local `data/` files are ignored by Git.

The existing `uv run python -m bookpath.bigquery` command still queries BigQuery
and prints a ten-row sample; it is not yet wired to save a full dataset.
The next step is to connect an explicit download to saving raw Parquet. After
that, preprocessing can read the raw local file and write a separate processed
Parquet file without querying BigQuery again.
