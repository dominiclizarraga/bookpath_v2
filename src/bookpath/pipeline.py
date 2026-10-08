"""Prepare a local document table from the saved raw books and TOC file."""

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from bookpath.documents import build_documents
from bookpath.local_data import read_books_from_parquet, save_books_to_parquet
from bookpath.toc import build_toc_features


def _file_checksum(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _validate_toc_snapshot(books, toc_features, raw_checksum):
    if (
        "source_sha256" not in toc_features
        or not toc_features["source_sha256"].eq(raw_checksum).all()
    ):
        raise ValueError("The saved TOC file does not identify this raw snapshot as its source.")
    expected = build_toc_features(books)
    expected["source_sha256"] = raw_checksum
    try:
        pd.testing.assert_frame_equal(toc_features, expected, check_exact=True)
    except AssertionError as error:
        raise ValueError(
            "The saved TOC file differs from the current TOC preparation. "
            "Rebuild it with uv run python -m bookpath.toc using a new --output path."
        ) from error


def prepare_documents(
    raw_path: str | Path,
    toc_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Verify local inputs, build documents, and save a separate versioned file.

    Both inputs must already exist. A full in-memory TOC rebuild checks that
    the saved TOC is current and complete; it does not replace that file.
    Existing outputs are protected. No downloads or model calls are made.
    """
    raw_path, toc_path, output_path = Path(raw_path), Path(toc_path), Path(output_path)
    if output_path.resolve() in {raw_path.resolve(), toc_path.resolve()}:
        raise ValueError("Document output and both input files must use different paths.")
    if output_path.exists():
        raise FileExistsError(f"Document file already exists: {output_path}")
    raw_checksum = _file_checksum(raw_path)
    toc_checksum = _file_checksum(toc_path)
    books = read_books_from_parquet(raw_path)
    toc_features = read_books_from_parquet(toc_path)
    _validate_toc_snapshot(books, toc_features, raw_checksum)
    documents = build_documents(books, toc_features)
    documents["raw_source_sha256"] = raw_checksum
    documents["toc_source_sha256"] = toc_checksum
    if _file_checksum(raw_path) != raw_checksum or _file_checksum(toc_path) != toc_checksum:
        raise RuntimeError("An input file changed during preparation; nothing saved.")
    return save_books_to_parquet(documents, output_path)


def main():
    parser = argparse.ArgumentParser(description="Build documents from saved local book data.")
    parser.add_argument("--input", default="data/raw/books.parquet", help="Saved raw books")
    parser.add_argument(
        "--toc", default="data/processed/toc_features.parquet", help="Saved TOC preparation",
    )
    parser.add_argument(
        "--output", default="data/processed/documents.parquet", help="New document file",
    )
    arguments = parser.parse_args()
    output = prepare_documents(arguments.input, arguments.toc, arguments.output)
    print(f"Saved documents to {output}")


if __name__ == "__main__":
    main()
