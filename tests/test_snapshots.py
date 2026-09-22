import pandas as pd
import pyarrow as pa
import pytest
from pandas.testing import assert_frame_equal

from bookpath import bigquery
from bookpath.snapshots import load_snapshot, save_snapshot


@pytest.fixture
def books():
    """Small invented records, including values that are easy to corrupt."""
    return pd.DataFrame(
        {
            "parent_asin": pd.Series(["0000000001", "0000000002", "0000000003"], dtype="string"),
            "isbn": pd.Series(["0012345678", pd.NA, "012345678X"], dtype="string"),
            "title": pd.Series(["Learning Python", "Data Basics", pd.NA], dtype="string"),
            "rating_count": pd.Series([12, pd.NA, 0], dtype="Int64"),
        }
    )


def test_parquet_round_trip_preserves_values_and_types(books, tmp_path):
    path = tmp_path / "raw" / "books.parquet"
    original = books.copy(deep=True)

    save_snapshot(books, path)
    restored = load_snapshot(path)

    assert_frame_equal(restored, original)
    assert_frame_equal(books, original)


def test_parquet_round_trip_preserves_nested_toc(books, tmp_path):
    books["toc_entries"] = [
        [{"sequence": 1, "text": "Introduction", "page": None},
         {"sequence": 2, "text": "Practice", "page": "10"}],
        [],
        None,
    ]
    path = tmp_path / "books.parquet"

    save_snapshot(books, path)
    restored = load_snapshot(path)

    # Parquet may return nested lists as arrays; compare their Arrow values/schema.
    expected = pa.Table.from_pandas(books, preserve_index=False)
    actual = pa.Table.from_pandas(restored, preserve_index=False)
    assert actual.equals(expected)


@pytest.mark.parametrize("snapshot_exists", [True, False])
def test_local_reader_never_calls_bigquery(books, tmp_path, monkeypatch, snapshot_exists):
    def unexpected_download(*args, **kwargs):
        pytest.fail("Local reads must never download from BigQuery")

    monkeypatch.setattr(bigquery, "load_books", unexpected_download)
    path = tmp_path / "books.parquet"

    if snapshot_exists:
        save_snapshot(books, path)
        assert_frame_equal(load_snapshot(path), books)
    else:
        with pytest.raises(FileNotFoundError, match="Download and save it explicitly"):
            load_snapshot(path)
        assert not path.exists()


def test_existing_snapshot_requires_explicit_overwrite(books, tmp_path):
    path = tmp_path / "books.parquet"
    save_snapshot(books, path)
    original_bytes = path.read_bytes()

    with pytest.raises(FileExistsError, match="already exists"):
        save_snapshot(books.iloc[:1], path)

    assert path.read_bytes() == original_bytes


def test_explicit_overwrite_saves_new_snapshot(books, tmp_path):
    path = tmp_path / "books.parquet"
    save_snapshot(books, path)
    replacement = books.iloc[:1].copy()

    save_snapshot(replacement, path, overwrite=True)

    assert_frame_equal(load_snapshot(path), replacement)


@pytest.mark.parametrize("snapshot_exists", [True, False])
def test_failed_write_never_publishes_partial_snapshot(
    books, tmp_path, monkeypatch, snapshot_exists
):
    path = tmp_path / "books.parquet"
    if snapshot_exists:
        save_snapshot(books, path)
    original_bytes = path.read_bytes() if snapshot_exists else None

    def interrupted_write(self, temporary_path, **kwargs):
        temporary_path.write_bytes(b"incomplete parquet data")
        raise OSError("Simulated disk failure")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", interrupted_write)

    with pytest.raises(OSError, match="Simulated disk failure"):
        save_snapshot(books, path, overwrite=True)

    if snapshot_exists:
        assert path.read_bytes() == original_bytes
    else:
        assert not path.exists()
    assert list(tmp_path.glob("*.tmp")) == []
