import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from bookpath.tfidf import build_book_corpus, rank_books


def example_documents():
    return pd.DataFrame([
        {"document_id": "a:toc:1", "parent_asin": "a", "book_title": "First",
         "text": "online business"},
        {"document_id": "a:features", "parent_asin": "a", "book_title": "First",
         "text": "finance"},
        {"document_id": "b:toc:1", "parent_asin": "b", "book_title": "Second",
         "text": "gardening flowers"},
    ])


def test_documents_are_joined_once_per_book_without_adding_the_title():
    corpus = build_book_corpus(example_documents())

    assert corpus["parent_asin"].tolist() == ["a", "b"]
    assert corpus["text"].tolist() == ["online business\nfinance", "gardening flowers"]
    assert corpus["document_count"].tolist() == [2, 1]


def test_exact_text_match_has_cosine_one_and_no_overlap_has_zero():
    corpus = build_book_corpus(example_documents())

    ranking, details = rank_books(corpus, "online business finance")

    assert ranking["parent_asin"].tolist() == ["a", "b"]
    assert ranking["cosine_similarity"].tolist() == pytest.approx([1.0, 0.0])
    assert ranking["rank"].tolist() == [1, 2]
    assert details["vocabulary_size"] == 5
    assert details["vectorizer_parameters"]["stop_words"] is None
    assert details["vectorizer_parameters"]["ngram_range"] == [1, 1]


def test_unseen_query_words_do_not_change_the_fitted_vocabulary():
    ranking, details = rank_books(build_book_corpus(example_documents()), "unseenword")

    assert ranking["cosine_similarity"].eq(0).all()
    assert details["query_terms_in_vocabulary"] == []
    assert details["query_terms_outside_vocabulary"] == ["unseenword"]
    assert details["vocabulary_size"] == 5


def test_equal_scores_are_ordered_by_book_id_regardless_of_input_order():
    corpus = build_book_corpus(example_documents()).iloc[::-1]

    ranking, _ = rank_books(corpus, "unseenword")

    assert ranking["parent_asin"].tolist() == ["a", "b"]


def test_inputs_are_preserved():
    documents = example_documents()
    original = documents.copy(deep=True)
    corpus = build_book_corpus(documents)
    original_corpus = corpus.copy(deep=True)

    rank_books(corpus, "business")

    assert_frame_equal(documents, original)
    assert_frame_equal(corpus, original_corpus)


def test_duplicate_document_ids_are_rejected():
    documents = example_documents()

    with pytest.raises(ValueError, match="unique"):
        build_book_corpus(pd.concat([documents, documents]))


def test_conflicting_titles_within_a_book_are_rejected():
    documents = example_documents()
    documents.loc[1, "book_title"] = "Different title"

    with pytest.raises(ValueError, match="title"):
        build_book_corpus(documents)


def test_blank_query_is_rejected():
    with pytest.raises(ValueError, match="query"):
        rank_books(build_book_corpus(example_documents()), "  ")
