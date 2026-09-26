import json

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from bookpath.toc import build_toc_features, prepare_toc_features


def books_with_toc(items):
    return pd.DataFrame([{
        "parent_asin": "0000000001",
        "ol_edition_key": "/books/OL1M",
        "title": "Example Book",
        "raw_toc_json": json.dumps(items),
    }])


def test_title_and_chapter_subtitle_form_the_feature_text():
    books = books_with_toc([{
        "title": "The New Rules",
        "subtitle": "How to Become the Smartest Person in Any Room",
        "label": "Chapter 1",
    }])

    entry = build_toc_features(books).iloc[0]

    assert entry["base_text"] == "The New Rules"
    assert entry["feature_text"] == (
        "The New Rules: How to Become the Smartest Person in Any Room"
    )
    assert entry["text_source"] == "title"
    assert entry["subtitle_added"]


def test_title_has_priority_over_value_and_label():
    books = books_with_toc([{"title": "Start", "value": "Other", "label": "1"}])

    entry = build_toc_features(books).iloc[0]

    assert entry["feature_text"] == "Start"
    assert entry["text_source"] == "title"


def test_blank_title_falls_back_to_value():
    books = books_with_toc([{"title": "  ", "value": "Volume One", "label": "1"}])

    entry = build_toc_features(books).iloc[0]

    assert entry["feature_text"] == "Volume One"
    assert entry["text_source"] == "value"


def test_missing_title_and_value_fall_back_to_label():
    books = books_with_toc([{"label": "Dedication"}])

    entry = build_toc_features(books).iloc[0]

    assert entry["feature_text"] == "Dedication"
    assert entry["text_source"] == "label"


def test_plain_string_item_is_supported():
    entry = build_toc_features(books_with_toc(["  Introduction  "])).iloc[0]

    assert entry["feature_text"] == "Introduction"
    assert entry["text_source"] == "plain_string"
    assert json.loads(entry["raw_item_json"]) == "  Introduction  "


def test_subtitle_already_in_title_is_not_added_twice():
    books = books_with_toc([{
        "title": "Negotiation: THE NEW RULES!", "subtitle": "The new rules",
    }])

    entry = build_toc_features(books).iloc[0]

    assert entry["feature_text"] == "Negotiation: THE NEW RULES!"
    assert not entry["subtitle_added"]


def test_subtitle_word_is_not_confused_with_part_of_another_word():
    entry = build_toc_features(
        books_with_toc([{"title": "Marketing", "subtitle": "Art"}])
    ).iloc[0]

    assert entry["feature_text"] == "Marketing: Art"


def test_subtitle_can_supply_text_when_main_text_is_missing():
    entry = build_toc_features(books_with_toc([{"subtitle": "A useful explanation"}])).iloc[0]

    assert pd.isna(entry["base_text"])
    assert entry["feature_text"] == "A useful explanation"
    assert entry["subtitle_added"]
    assert not entry["missing_text"]


def test_empty_item_is_flagged_without_losing_its_original_position():
    features = build_toc_features(books_with_toc([
        {"title": "First"}, {"value": ""}, {"title": "Third"},
    ]))

    assert features["raw_position"].tolist() == [1, 2, 3]
    assert features["missing_text"].tolist() == [False, True, False]
    assert pd.isna(features.iloc[1]["feature_text"])


def test_numeric_only_text_is_flagged_without_deleting_it():
    features = build_toc_features(books_with_toc([{"title": "15"}]))

    assert features.iloc[0]["feature_text"] == "15"
    assert features.iloc[0]["numeric_only_text"]


def test_repeated_text_is_flagged_within_each_book():
    first_book = books_with_toc(["Introduction", " INTRODUCTION "])
    second_book = books_with_toc(["Introduction"])
    second_book["parent_asin"] = "0000000002"

    features = build_toc_features(pd.concat([first_book, second_book], ignore_index=True))

    assert features["repeated_text"].tolist() == [True, True, False]


def test_context_and_unknown_raw_fields_are_preserved():
    raw_item = {
        "title": "Introduction", "label": "Chapter 1", "level": 0,
        "pagenum": "ix", "class": "chapter", "authors": [{"name": "An Author"}],
        "description": {"value": "Background note"}, "unexpected_key": ["Keep me"],
    }

    entry = build_toc_features(books_with_toc([raw_item])).iloc[0]

    assert entry["parent_asin"] == "0000000001"
    assert entry["ol_edition_key"] == "/books/OL1M"
    assert entry["label"] == "Chapter 1"
    assert entry["level"] == "0"
    assert entry["page"] == "ix"
    assert entry["entry_class"] == "chapter"
    assert json.loads(entry["authors_json"]) == raw_item["authors"]
    assert json.loads(entry["description_json"]) == raw_item["description"]
    assert json.loads(entry["raw_item_json"]) == raw_item


def test_building_features_does_not_change_the_input():
    books = books_with_toc([{"title": "  Introduction  "}])
    original = books.copy(deep=True)

    build_toc_features(books)

    assert_frame_equal(books, original)


def test_empty_input_has_the_output_columns():
    features = build_toc_features(books_with_toc([]).iloc[:0])

    assert features.empty
    assert {"parent_asin", "feature_text", "missing_text"} <= set(features.columns)


def test_invalid_json_names_the_affected_book():
    books = books_with_toc([])
    books["raw_toc_json"] = "not JSON"

    with pytest.raises(ValueError, match="0000000001.*invalid raw_toc_json"):
        build_toc_features(books)


def test_raw_toc_must_be_a_list():
    with pytest.raises(ValueError, match="0000000001.*list"):
        build_toc_features(books_with_toc({"title": "Wrong container"}))


def test_unsupported_raw_item_names_the_book_and_position():
    with pytest.raises(ValueError, match="0000000001.*item 2"):
        build_toc_features(books_with_toc(["Valid", 123]))


def test_duplicate_book_ids_are_rejected():
    book = books_with_toc(["Introduction"])

    with pytest.raises(ValueError, match="parent_asin.*unique"):
        build_toc_features(pd.concat([book, book], ignore_index=True))


def test_local_preprocessing_saves_features_and_preserves_raw_file(tmp_path):
    raw_path = tmp_path / "raw.parquet"
    output_path = tmp_path / "processed.parquet"
    books_with_toc([{"title": "Start", "subtitle": "A practical guide"}]).to_parquet(raw_path)
    original_bytes = raw_path.read_bytes()

    prepare_toc_features(raw_path, output_path)

    features = pd.read_parquet(output_path)
    assert features["feature_text"].tolist() == ["Start: A practical guide"]
    assert features["feature_version"].tolist() == ["toc-v1"]
    assert len(features.iloc[0]["source_sha256"]) == 64
    assert raw_path.read_bytes() == original_bytes


def test_existing_processed_file_is_not_overwritten(tmp_path):
    output_path = tmp_path / "processed.parquet"
    output_path.write_bytes(b"Existing output")

    with pytest.raises(FileExistsError):
        prepare_toc_features(tmp_path / "raw.parquet", output_path)

    assert output_path.read_bytes() == b"Existing output"


def test_processed_path_cannot_be_the_raw_path(tmp_path):
    path = tmp_path / "books.parquet"

    with pytest.raises(ValueError, match="different"):
        prepare_toc_features(path, path)
