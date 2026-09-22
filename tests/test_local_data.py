import pandas as pd
import pyarrow as pa
import pytest
from pandas.testing import assert_frame_equal

from bookpath import bigquery
from bookpath.local_data import read_books_from_parquet, save_books_to_parquet


@pytest.fixture
def books():
    """Small invented records, including values that are easy to corrupt."""
    return pd.DataFrame(
        {
            "parent_asin": pd.Series(
                ["0000000001", "0000000002", "0000000003"], dtype="string"
            ),
            "isbn": pd.Series(["0012345678", pd.NA, "012345678X"], dtype="string"),
            "title": pd.Series(
                ["Learning Python", "Data Basics", pd.NA], dtype="string"
            ),
            "rating_count": pd.Series([12, pd.NA, 0], dtype="Int64"),
        }
    )


def test_parquet_round_trip_preserves_values_and_types(books, tmp_path):
    path = tmp_path / "raw" / "books.parquet"
    original = books.copy(deep=True)

    saved_path = save_books_to_parquet(books, path)
    restored = read_books_from_parquet(path)

    assert saved_path == path
    assert_frame_equal(restored, original)
    assert_frame_equal(books, original)


def test_parquet_round_trip_preserves_nested_toc(books, tmp_path):
    books["toc_entries"] = [
        [
            {"sequence": 1, "text": "Introduction", "page": None},
            {"sequence": 2, "text": "Practice", "page": "10"},
        ],
        [],
        None,
    ]
    path = tmp_path / "books.parquet"

    save_books_to_parquet(books, path)
    restored = read_books_from_parquet(path)

    # Parquet may return nested lists as arrays; compare their Arrow values/schema.
    expected = pa.Table.from_pandas(books, preserve_index=False)
    actual = pa.Table.from_pandas(restored, preserve_index=False)
    assert actual.equals(expected)


def test_reads_existing_parquet_without_download(books, tmp_path, monkeypatch):
    def unexpected_download(*args, **kwargs):
        pytest.fail("Local reads must never download from BigQuery")

    monkeypatch.setattr(bigquery, "load_books", unexpected_download)
    path = tmp_path / "books.parquet"

    save_books_to_parquet(books, path)

    restored_books = read_books_from_parquet(path)

    assert_frame_equal(restored_books, books)


def test_missing_parquet_raises_without_download(tmp_path, monkeypatch):
    def unexpected_download(*args, **kwargs):
        pytest.fail("Local reads must never download from BigQuery")

    monkeypatch.setattr(bigquery, "load_books", unexpected_download)
    path = tmp_path / "books.parquet"

    with pytest.raises(FileNotFoundError, match="Download and save it explicitly"):
        read_books_from_parquet(path)

    assert not path.exists()


def test_existing_parquet_file_requires_explicit_overwrite(books, tmp_path):
    path = tmp_path / "books.parquet"
    save_books_to_parquet(books, path)
    original_bytes = path.read_bytes()

    with pytest.raises(FileExistsError, match="already exists"):
        save_books_to_parquet(books.iloc[:1], path)

    assert path.read_bytes() == original_bytes


def test_explicit_overwrite_replaces_saved_books(books, tmp_path):
    path = tmp_path / "books.parquet"
    save_books_to_parquet(books, path)
    replacement = books.iloc[:1].copy()

    save_books_to_parquet(replacement, path, overwrite=True)

    assert_frame_equal(read_books_from_parquet(path), replacement)


def test_failed_overwrite_preserves_existing_file(books, tmp_path, monkeypatch):
    path = tmp_path / "books.parquet"
    save_books_to_parquet(books, path)
    original_bytes = path.read_bytes()

    def interrupted_write(self, temporary_path, **kwargs):
        temporary_path.write_bytes(b"incomplete parquet data")
        raise OSError("Simulated disk failure")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", interrupted_write)

    with pytest.raises(OSError, match="Simulated disk failure"):
        save_books_to_parquet(books, path, overwrite=True)

    assert path.read_bytes() == original_bytes
    assert list(tmp_path.glob("*.tmp")) == []


def test_failed_save_does_not_create_destination_file(books, tmp_path, monkeypatch):
    path = tmp_path / "books.parquet"

    def interrupted_write(self, temporary_path, **kwargs):
        temporary_path.write_bytes(b"incomplete parquet data")
        raise OSError("Simulated disk failure")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", interrupted_write)

    with pytest.raises(OSError, match="Simulated disk failure"):
        save_books_to_parquet(books, path)

    assert not path.exists()
    assert list(tmp_path.glob("*.tmp")) == []
