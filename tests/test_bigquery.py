import json
import subprocess

import pandas as pd
import pyarrow as pa
import pytest
from pandas.testing import assert_frame_equal

from bookpath import bigquery
from bookpath.bigquery import load_books
from bookpath.local_data import read_books_from_parquet, save_books_to_parquet


@pytest.fixture
def download_environment(tmp_path, monkeypatch):
    """Use a temporary working directory and invented cloud configuration."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bigquery, "load_dotenv", lambda: None)
    monkeypatch.setenv("BOOKPATH_GCP_PROJECT", "test-project")
    monkeypatch.setenv("BOOKPATH_BQ_DATASET", "dataset")
    monkeypatch.setenv("BOOKPATH_BQ_TABLE", "books")
    monkeypatch.setenv("BOOKPATH_BQ_LOCATION", "asia-northeast1")
    return tmp_path


def test_load_books_returns_query_records_as_dataframe(monkeypatch):
    records = [{"parent_asin": "0000000001", "toc_entries": [{"text": "Intro"}]}]

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, json.dumps(records), "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    books = load_books(
        "test-project", "dataset", "books", "asia-northeast1", max_rows=10
    )

    assert_frame_equal(books, pd.DataFrame(records))


def test_load_books_requests_the_selected_table_location_and_row_limit(monkeypatch):
    """The CLI request is the external boundary, not an internal helper."""
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "[]", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    load_books("test-project", "dataset", "books", "asia-northeast1", max_rows=10)

    assert len(commands) == 1
    command = commands[0]
    assert command[:3] == ["bq", "--location=asia-northeast1", "query"]
    assert "--max_rows=10" in command
    assert "--use_legacy_sql=false" in command
    assert "--format=json" in command
    assert command[-1] == (
        "SELECT * FROM `test-project.dataset.books` ORDER BY parent_asin LIMIT 10"
    )


def test_load_books_reports_bigquery_failure_and_preserves_cause(monkeypatch):
    original_error = subprocess.CalledProcessError(
        1, ["bq"], output="", stderr="Access denied to test table"
    )

    def fake_run(*args, **kwargs):
        raise original_error

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Access denied to test table") as caught:
        load_books("test-project", "dataset", "books", "asia-northeast1")

    assert caught.value.__cause__ is original_error


def test_main_saves_and_reads_back_downloaded_sample(
    download_environment, monkeypatch, capsys
):
    records = [
        {"parent_asin": "0000000001", "toc_entries": [{"text": "Intro"}]},
        {"parent_asin": "0000000002", "toc_entries": None},
    ]
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps(records), "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    bigquery.main()

    saved_books = read_books_from_parquet(
        download_environment / "data/raw/books_sample.parquet"
    )
    expected = pa.Table.from_pandas(pd.DataFrame(records), preserve_index=False)
    actual = pa.Table.from_pandas(saved_books, preserve_index=False)
    assert actual.equals(expected)
    assert len(commands) == 1
    assert "--max_rows=10" in commands[0]
    assert "Read back: 2 books" in capsys.readouterr().out


def test_main_skips_existing_sample_without_querying_bigquery(download_environment, capsys):
    path = download_environment / "data/raw/books_sample.parquet"
    save_books_to_parquet(pd.DataFrame({"parent_asin": ["0000000001"]}), path)
    original_bytes = path.read_bytes()

    # The shared test fixture fails if any external command is attempted.
    bigquery.main()

    assert path.read_bytes() == original_bytes
    assert "Skipping BigQuery" in capsys.readouterr().out


def test_main_failed_download_does_not_create_parquet(download_environment, monkeypatch):
    def failed_query(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["bq"], stderr="Access denied")

    monkeypatch.setattr(subprocess, "run", failed_query)

    with pytest.raises(RuntimeError, match="Access denied"):
        bigquery.main()

    assert not (download_environment / "data/raw/books_sample.parquet").exists()


def test_main_saves_ten_thousand_books_to_selected_file(download_environment, monkeypatch):
    records = [{"parent_asin": f"{number:010d}"} for number in range(10_000)]

    def fake_run(command, **kwargs):
        assert "--max_rows=10000" in command
        assert command[-1].endswith("LIMIT 10000")
        return subprocess.CompletedProcess(command, 0, json.dumps(records), "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    bigquery.main(max_rows=10_000, output_path="data/raw/books.parquet")

    saved_books = read_books_from_parquet(download_environment / "data/raw/books.parquet")
    assert_frame_equal(saved_books, pd.DataFrame(records))
    assert not (download_environment / "data/raw/books_sample.parquet").exists()


def test_main_skips_existing_selected_file_without_download(download_environment, capsys):
    path = download_environment / "data/raw/books.parquet"
    save_books_to_parquet(pd.DataFrame({"parent_asin": ["0000000001"]}), path)
    original_bytes = path.read_bytes()

    bigquery.main(max_rows=10_000, output_path=path)

    assert path.read_bytes() == original_bytes
    assert "Skipping BigQuery" in capsys.readouterr().out


def test_main_rejects_zero_rows_before_download(download_environment):
    with pytest.raises(ValueError, match="greater than zero"):
        bigquery.main(max_rows=0, output_path="data/raw/books.parquet")

    assert not (download_environment / "data/raw/books.parquet").exists()


def test_load_books_rejects_negative_row_limit():
    with pytest.raises(ValueError, match="greater than zero"):
        load_books("test-project", "dataset", "books", "asia-northeast1", max_rows=-1)
