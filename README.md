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

## Local snapshots

Once a download has produced a `books` DataFrame, save it explicitly:

```python
from bookpath.snapshots import save_snapshot

save_snapshot(books, "data/raw/books.parquet")
```

For later exploration or preprocessing, read the local file:

```python
from bookpath.snapshots import load_snapshot

books = load_snapshot("data/raw/books.parquet")
```

Loading never downloads data. A missing snapshot raises `FileNotFoundError`.
Saving protects existing files unless `overwrite=True` is given, and failed
writes leave the previous snapshot intact. Book identifiers must be columns;
the DataFrame index is not saved. Local `data/` files are ignored by Git.

The existing `uv run python -m bookpath.bigquery` command still queries BigQuery
and prints a ten-row sample; it is not yet wired to save a full snapshot.
