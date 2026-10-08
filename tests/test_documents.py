import json
from copy import deepcopy

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from bookpath.documents import build_documents
from bookpath.toc import build_toc_features


def example_books(features=None, description=None, toc=None):
    return pd.DataFrame([{
        "parent_asin": "0000000001",
        "title": "Learning Python",
        "ol_edition_key": "/books/OL1M",
        "raw_toc_json": json.dumps(toc if toc is not None else ["Start"]),
        "features": features if features is not None else ["A useful guide"],
        "description": description if description is not None else ["More detail"],
    }])


def test_features_are_joined_in_order_and_take_priority_over_description():
    books = example_books(features=["  Learn Python ", " ", "Practice", "Practice"])

    documents = build_documents(books, build_toc_features(books))
    book_text = documents.loc[documents["source"].ne("toc")].iloc[0]

    assert book_text["text"] == "Learn Python\nPractice\nPractice"
    assert book_text["source"] == "features"
    assert book_text["document_id"] == "0000000001:features"
    assert book_text["book_title"] == "Learning Python"
    assert pd.isna(book_text["raw_position"])
    assert pd.isna(book_text["repeated_text"])
    assert pd.isna(book_text["numeric_only_text"])


def test_blank_features_fall_back_to_description():
    books = example_books(features=[" ", "\n"], description=[" A guide ", "With exercises"])

    documents = build_documents(books, build_toc_features(books))
    fallback = documents.loc[documents["source"].eq("description")].iloc[0]

    assert fallback["text"] == "A guide\nWith exercises"
    assert fallback["document_id"] == "0000000001:description"
    assert documents["source"].tolist() == ["toc", "description"]


def test_books_without_either_book_level_text_still_keep_their_toc():
    books = example_books(features=[], description=[])

    documents = build_documents(books, build_toc_features(books))

    assert documents["source"].tolist() == ["toc"]
    assert documents["text"].tolist() == ["Start"]


def test_missing_toc_text_is_skipped_without_renumbering_or_deleting_flagged_text():
    books = example_books(features=[], description=[], toc=["15", {}, "Start", "Start"])
    toc = build_toc_features(books)

    documents = build_documents(books, toc)

    assert documents["raw_position"].tolist() == [1, 3, 4]
    assert documents["text"].tolist() == ["15", "Start", "Start"]
    assert documents["numeric_only_text"].tolist() == [True, False, False]
    assert documents["repeated_text"].tolist() == [False, True, True]
    assert documents["document_id"].tolist() == [
        "0000000001:toc:1", "0000000001:toc:3", "0000000001:toc:4",
    ]
    assert len(toc) == 4


def test_whitespace_only_toc_text_is_skipped():
    books = example_books(features=[], description=[])
    toc = build_toc_features(books)
    toc.loc[0, "feature_text"] = " \n "

    assert build_documents(books, toc).empty


def test_order_and_document_ids_are_stable_when_input_rows_are_reordered():
    first = example_books(toc=["Start", "Next"])
    second = example_books(toc=["Other"])
    second["parent_asin"] = "0000000002"
    books = pd.concat([second, first], ignore_index=True)
    toc = build_toc_features(books)

    expected = build_documents(books, toc)
    reordered = build_documents(books.iloc[::-1], toc.iloc[::-1])

    assert_frame_equal(reordered, expected)
    assert expected["document_id"].is_unique


def test_building_documents_preserves_both_inputs():
    books = example_books(features=["  Keep these spaces  ", ""], toc=[{}, "Start"])
    toc = build_toc_features(books)
    original_pieces = deepcopy(books["features"].tolist())
    original_books = books.copy(deep=True)
    original_toc = toc.copy(deep=True)

    build_documents(books, toc)

    assert books["features"].tolist() == original_pieces
    assert_frame_equal(books, original_books)
    assert_frame_equal(toc, original_toc)


def test_empty_input_keeps_the_document_schema():
    books = example_books().iloc[:0]

    documents = build_documents(books, build_toc_features(books))

    assert documents.empty
    assert len(documents.columns) == 9
    assert str(documents["raw_position"].dtype) == "Int64"
    assert str(documents["repeated_text"].dtype) == "boolean"


@pytest.mark.parametrize("bad_pieces", ["one string", None, {"a": "value"}, {"unordered"}])
def test_invalid_text_containers_name_the_book_and_column(bad_pieces):
    books = example_books()
    books.at[0, "features"] = bad_pieces

    with pytest.raises(ValueError, match="0000000001.*features.*list or array"):
        build_documents(books, build_toc_features(books))


def test_nontext_description_pieces_are_rejected_even_when_features_are_available():
    books = example_books(description=["Valid", 123])

    with pytest.raises(ValueError, match="0000000001.*description.*piece 2.*text"):
        build_documents(books, build_toc_features(books))


def test_duplicate_book_ids_are_rejected():
    books = example_books()
    toc = build_toc_features(books)

    with pytest.raises(ValueError, match="parent_asin.*unique"):
        build_documents(pd.concat([books, books]), toc)


def test_toc_rows_for_unknown_books_are_rejected():
    books = example_books()
    toc = build_toc_features(books)
    toc.loc[0, "parent_asin"] = "unknown"

    with pytest.raises(ValueError, match="unknown book"):
        build_documents(books, toc)


def test_duplicate_toc_positions_are_rejected():
    books = example_books()
    toc = build_toc_features(books)

    with pytest.raises(ValueError, match="raw_position.*unique"):
        build_documents(books, pd.concat([toc, toc]))


def test_missing_required_source_column_is_rejected():
    books = example_books()

    with pytest.raises(ValueError, match="Missing book columns: features"):
        build_documents(books.drop(columns="features"), build_toc_features(books))
