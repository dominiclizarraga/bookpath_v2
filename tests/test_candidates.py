import pandas as pd
import pytest

from bookpath.candidates import build_candidates
from bookpath.tfidf import build_book_corpus, rank_books


def documents():
    return pd.DataFrame([
        {"document_id": "a:toc:1", "parent_asin": "a", "book_title": "Business",
         "text": "online business"},
        {"document_id": "b:toc:1", "parent_asin": "b", "book_title": "Gardening",
         "text": "gardening flowers"},
    ])


def query(identifier="q1", text="online business"):
    return {"query_id": identifier, "query": text, "background": "Beginner",
            "topic": "Business", "success_criterion": "Useful business guidance."}


def test_candidates_match_the_unchanged_baseline_and_preserve_full_ranking():
    frame = documents()

    rankings, candidate_queries = build_candidates(frame, [query()], top_k=1)
    expected, _ = rank_books(build_book_corpus(frame), query()["query"])

    pd.testing.assert_frame_equal(rankings.drop(columns="query_id"), expected)
    assert len(rankings) == 2
    assert candidate_queries[0]["books"] == expected.head(1).to_dict(orient="records")
    assert candidate_queries[0]["success_criterion"] == query()["success_criterion"]


def test_query_text_alone_drives_retrieval_without_appending_the_rubric():
    record = query(text="gardening flowers")
    record["background"] = "online business"
    record["success_criterion"] = "online business"

    rankings, _ = build_candidates(documents(), [record])

    assert rankings.iloc[0]["parent_asin"] == "b"
    assert rankings.iloc[0]["cosine_similarity"] == pytest.approx(1)


def test_multiple_queries_have_separate_ranks():
    rankings, _ = build_candidates(documents(), [query(), query("q2", "gardening")])

    assert rankings.groupby("query_id")["rank"].apply(list).to_dict() == {
        "q1": [1, 2], "q2": [1, 2],
    }


def test_duplicate_query_ids_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        build_candidates(documents(), [query(), query()])
