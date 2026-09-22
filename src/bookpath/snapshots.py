"""Save and read local book snapshots without contacting BigQuery."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd


def load_snapshot(path: str | Path) -> pd.DataFrame:
    """Read a saved Parquet file; missing files never trigger a download."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Book snapshot not found: {path}. Download and save it explicitly first."
        )
    return pd.read_parquet(path, engine="pyarrow")


def save_snapshot(
    books: pd.DataFrame, path: str | Path, *, overwrite: bool = False
) -> Path:
    """Save books atomically, preserving an existing file if writing fails.

    Existing snapshots are protected unless overwrite=True is explicitly given.
    The DataFrame's index is not saved; book identifiers belong in columns.
    """
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Snapshot already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    # A temporary file in the same directory allows an atomic final rename.
    with NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)

    try:
        books.to_parquet(temporary_path, engine="pyarrow", index=False)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return path
