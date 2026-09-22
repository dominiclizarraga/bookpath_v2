import json
import subprocess

import pytest

from bookpath.bigquery import load_books


def test_load_books_parses_mocked_query_output(monkeypatch):
    records = [{"parent_asin": "0000000001", "toc_entries": [{"text": "Intro"}]}]

    def fake_run(command, **kwargs):
        assert command[0] == "bq"
        assert "--max_rows=10" in command
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is True
        return subprocess.CompletedProcess(command, 0, json.dumps(records), "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    books = load_books("test-project", "dataset", "books", "asia-northeast1", max_rows=10)

    assert books.to_dict("records") == records


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
