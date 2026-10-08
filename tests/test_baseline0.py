import hashlib
import json

import pandas as pd
import pytest

from bookpath.baseline0 import run_baseline


def test_run_saves_every_book_and_keeps_quality_metrics_unmeasured(tmp_path):
    documents_path = tmp_path / "documents.parquet"
    query_path = tmp_path / "query.json"
    output_dir = tmp_path / "baseline"
    pd.DataFrame([
        {"document_id": "a:toc:1", "parent_asin": "a", "book_title": "First",
         "text": "online business"},
        {"document_id": "b:toc:1", "parent_asin": "b", "book_title": "Second",
         "text": "gardening flowers"},
    ]).to_parquet(documents_path, index=False)
    query_path.write_text(json.dumps({"query_id": "q1", "query": "online business"}))
    original = documents_path.read_bytes()

    result = run_baseline(documents_path, query_path, output_dir)
    ranking = pd.read_parquet(result / "ranking.parquet")
    metadata = json.loads((result / "run.json").read_text())

    assert ranking["parent_asin"].tolist() == ["a", "b"]
    assert metadata["query"] == "online business"
    assert metadata["ranked_books"] == 2
    assert metadata["tuned"] is False
    assert metadata["metrics"] == {
        "nDCG@5": None, "Recall@10": None, "MRR": None, "Precision@5": None,
    }
    assert metadata["documents_sha256"] == hashlib.sha256(original).hexdigest()
    assert documents_path.read_bytes() == original


def test_existing_run_cannot_be_overwritten(tmp_path):
    output_dir = tmp_path / "baseline"
    output_dir.mkdir()
    saved = output_dir / "run.json"
    saved.write_text("Existing run")

    with pytest.raises(FileExistsError):
        run_baseline(tmp_path / "missing.parquet", tmp_path / "missing.json", output_dir)

    assert saved.read_text() == "Existing run"
