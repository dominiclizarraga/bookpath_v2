import hashlib
import json

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from bookpath import pipeline
from bookpath.toc import prepare_toc_features


@pytest.fixture
def source_paths(tmp_path):
    raw_path = tmp_path / "books.parquet"
    toc_path = tmp_path / "toc.parquet"
    pd.DataFrame([{
        "parent_asin": "0000000001", "title": "Python",
        "ol_edition_key": "/books/OL1M", "raw_toc_json": json.dumps([{}, "Practice"]),
        "features": [" Learn ", "By doing"], "description": [],
    }]).to_parquet(raw_path, index=False)
    prepare_toc_features(raw_path, toc_path)
    return raw_path, toc_path


def test_pipeline_writes_traceable_documents_and_preserves_inputs(source_paths, tmp_path):
    raw_path, toc_path = source_paths
    original_raw, original_toc = raw_path.read_bytes(), toc_path.read_bytes()
    output = tmp_path / "documents.parquet"

    result = pipeline.prepare_documents(raw_path, toc_path, output)
    documents = pd.read_parquet(result)

    assert result == output
    assert documents["text"].tolist() == ["Practice", "Learn\nBy doing"]
    assert documents["raw_position"].iloc[0] == 2
    assert documents["document_version"].eq("documents-v1").all()
    assert documents["raw_source_sha256"].eq(hashlib.sha256(original_raw).hexdigest()).all()
    assert documents["toc_source_sha256"].eq(hashlib.sha256(original_toc).hexdigest()).all()
    assert raw_path.read_bytes() == original_raw
    assert toc_path.read_bytes() == original_toc


def test_rebuilding_to_another_path_gives_identical_values(source_paths, tmp_path):
    first = pipeline.prepare_documents(*source_paths, tmp_path / "first.parquet")
    second = pipeline.prepare_documents(*source_paths, tmp_path / "second.parquet")

    assert_frame_equal(pd.read_parquet(first), pd.read_parquet(second))


def test_existing_output_is_not_overwritten(tmp_path):
    output = tmp_path / "documents.parquet"
    output.write_bytes(b"Existing output")

    with pytest.raises(FileExistsError):
        pipeline.prepare_documents(tmp_path / "missing.parquet", tmp_path / "toc.parquet", output)

    assert output.read_bytes() == b"Existing output"


@pytest.mark.parametrize("input_index", [0, 1])
def test_output_cannot_replace_either_input(source_paths, input_index):
    with pytest.raises(ValueError, match="different"):
        pipeline.prepare_documents(*source_paths, source_paths[input_index])


def test_missing_toc_file_does_not_create_output(source_paths, tmp_path):
    output = tmp_path / "documents.parquet"

    with pytest.raises(FileNotFoundError):
        pipeline.prepare_documents(source_paths[0], tmp_path / "missing.parquet", output)

    assert not output.exists()


def test_toc_from_a_different_raw_snapshot_is_rejected(source_paths, tmp_path):
    raw_path, toc_path = source_paths
    raw = pd.read_parquet(raw_path)
    raw.at[0, "features"] = ["Different snapshot"]
    raw.to_parquet(raw_path, index=False)
    output = tmp_path / "documents.parquet"

    with pytest.raises(ValueError, match="raw snapshot"):
        pipeline.prepare_documents(raw_path, toc_path, output)

    assert not output.exists()


@pytest.mark.parametrize("column,value", [
    ("feature_text", "Unexpected text"), ("feature_version", "old-version"),
])
def test_changed_toc_output_is_rejected(source_paths, tmp_path, column, value):
    raw_path, toc_path = source_paths
    toc = pd.read_parquet(toc_path)
    toc.loc[1, column] = value
    toc.to_parquet(toc_path, index=False)
    output = tmp_path / "documents.parquet"

    with pytest.raises(ValueError, match="current TOC preparation"):
        pipeline.prepare_documents(raw_path, toc_path, output)

    assert not output.exists()


def test_missing_toc_rows_are_rejected(source_paths, tmp_path):
    raw_path, toc_path = source_paths
    pd.read_parquet(toc_path).iloc[1:].to_parquet(toc_path, index=False)
    output = tmp_path / "documents.parquet"

    with pytest.raises(ValueError, match="current TOC preparation"):
        pipeline.prepare_documents(raw_path, toc_path, output)

    assert not output.exists()


def test_input_change_during_reading_prevents_output(source_paths, tmp_path, monkeypatch):
    raw_path, toc_path = source_paths
    read_parquet = pd.read_parquet

    def read_then_change_file(path, *args, **kwargs):
        frame = read_parquet(path, *args, **kwargs)
        if path == raw_path:
            raw_path.write_bytes(raw_path.read_bytes() + b"changed")
        return frame

    monkeypatch.setattr(pd, "read_parquet", read_then_change_file)
    output = tmp_path / "documents.parquet"

    with pytest.raises(RuntimeError, match="changed"):
        pipeline.prepare_documents(raw_path, toc_path, output)

    assert not output.exists()
