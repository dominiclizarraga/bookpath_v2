import json
import subprocess

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from bookpath.bigquery import load_books


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
    assert command[-1] == "SELECT * FROM `test-project.dataset.books` ORDER BY parent_asin"


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
