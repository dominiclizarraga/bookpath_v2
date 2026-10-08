"""Untuned, book-level TF-IDF retrieval with cosine similarity."""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def build_book_corpus(documents: pd.DataFrame) -> pd.DataFrame:
    """Join prepared texts in saved order; keep titles as display metadata."""
    required = ["document_id", "parent_asin", "book_title", "text"]
    missing = set(required).difference(documents.columns)
    if missing:
        raise ValueError(f"Missing document columns: {', '.join(sorted(missing))}")
    if documents.empty:
        raise ValueError("The document table must contain at least one book.")
    for column in required:
        if not all(isinstance(value, str) and value.strip() for value in documents[column]):
            raise ValueError(f"Document {column} must contain nonblank text.")
    if not documents["document_id"].is_unique:
        raise ValueError("Document IDs must be unique.")
    groups = documents.groupby("parent_asin", sort=True)
    if groups["book_title"].nunique().gt(1).any():
        raise ValueError("Every book must have one consistent title.")
    return groups.agg(
        book_title=("book_title", "first"),
        text=("text", "\n".join),
        document_count=("document_id", "size"),
    ).reset_index()


def _parameter_record(vectorizer):
    parameters = vectorizer.get_params(deep=False)
    # JSON represents tuples as lists and cannot directly store Python types.
    return {
        name: value.__name__ if isinstance(value, type)
        else list(value) if isinstance(value, tuple) else value
        for name, value in parameters.items()
    }


def rank_books(corpus: pd.DataFrame, query: str) -> tuple[pd.DataFrame, dict]:
    """Fit library defaults on books, transform the query, and rank every book.

    The query never contributes to the fitted vocabulary or IDF weights.
    Score ties are resolved by book ID, without relevance-based reranking.
    No labels, quality metrics, or parameter search are used here.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("The query must contain nonblank text.")
    vectorizer = TfidfVectorizer()
    book_vectors = vectorizer.fit_transform(corpus["text"])
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, book_vectors).ravel()
    ranking = corpus[["parent_asin", "book_title"]].copy()
    ranking["cosine_similarity"] = scores
    ranking = ranking.sort_values(
        ["cosine_similarity", "parent_asin"], ascending=[False, True],
    ).reset_index(drop=True)
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    terms = sorted(set(vectorizer.build_analyzer()(query)))
    details = {
        "vocabulary_size": len(vectorizer.vocabulary_),
        "vectorizer_parameters": _parameter_record(vectorizer),
        "query_terms_in_vocabulary": [term for term in terms if term in vectorizer.vocabulary_],
        "query_terms_outside_vocabulary": [term for term in terms if term not in vectorizer.vocabulary_],
    }
    return ranking, details
