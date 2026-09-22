"""Read and save local book data as Parquet, without contacting BigQuery."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd


def read_books_from_parquet(parquet_path: str | Path) -> pd.DataFrame:
    """Read a saved Parquet file; missing files never trigger a download."""
    parquet_path = Path(parquet_path)
    if not parquet_path.is_file():
        raise FileNotFoundError(
            f"Book Parquet file not found: {parquet_path}. "
            "Download and save it explicitly first."
        )
    return pd.read_parquet(parquet_path, engine="pyarrow")


def save_books_to_parquet(
    books: pd.DataFrame, parquet_path: str | Path, *, overwrite: bool = False
) -> Path:
    """Save a DataFrame to a local Parquet file and return its path.

    Write to a temporary file first, then move the completed file into place.
    This keeps a failed write from damaging an existing dataset. Replacing an
    existing file requires overwrite=True. Book identifiers must be columns;
    the DataFrame's index is not saved. The input DataFrame is not modified.
    """
    parquet_path = Path(parquet_path)
    if parquet_path.exists() and not overwrite:
        raise FileExistsError(f"Book Parquet file already exists: {parquet_path}")

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    # 1. Create a temporary file beside the destination so the move is atomic.
    with NamedTemporaryFile(
        dir=parquet_path.parent,
        prefix=f".{parquet_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_file_path = Path(temporary_file.name)

    try:
        # 2. Finish writing before making the destination available to readers.
        books.to_parquet(temporary_file_path, engine="pyarrow", index=False)
        os.replace(temporary_file_path, parquet_path)
    finally:
        # 3. Remove any incomplete file if writing failed; after a move it is gone.
        temporary_file_path.unlink(missing_ok=True)

    return parquet_path
