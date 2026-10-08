"""Build traceable text documents from saved books and prepared TOC entries."""

from collections.abc import Mapping

import pandas as pd


DOCUMENT_VERSION = "documents-v1"
STRING_COLUMNS = [
    "document_id", "parent_asin", "book_title", "source", "text", "document_version",
]
DOCUMENT_COLUMNS = [
    "document_id", "parent_asin", "book_title", "source", "raw_position", "text",
    "numeric_only_text", "repeated_text", "document_version",
]
TOC_COLUMNS = [
    "parent_asin", "raw_position", "feature_text", "numeric_only_text", "repeated_text",
]


def _require_columns(frame, columns, name):
    missing = set(columns).difference(frame.columns)
    if missing:
        raise ValueError(f"Missing {name} columns: {', '.join(sorted(missing))}")


def _validate_books(books):
    _require_columns(books, ["parent_asin", "title", "features", "description"], "book")
    for column in ["parent_asin", "title"]:
        if not all(isinstance(value, str) and value.strip() for value in books[column]):
            raise ValueError(f"{column} must contain nonblank text.")
    if books["parent_asin"].duplicated().any():
        raise ValueError("parent_asin must be unique: one row per Amazon parent record.")


def _validate_toc(books, toc_features):
    _require_columns(toc_features, TOC_COLUMNS, "TOC")
    if not toc_features["parent_asin"].isin(books["parent_asin"]).all():
        raise ValueError("TOC rows refer to an unknown book; check parent_asin.")
    positions = toc_features["raw_position"]
    if (
        not pd.api.types.is_integer_dtype(positions)
        or positions.isna().any()
        or positions.le(0).any()
    ):
        raise ValueError("TOC raw_position must contain positive integers.")
    if toc_features.duplicated(["parent_asin", "raw_position"]).any():
        raise ValueError("TOC raw_position must be unique within each book.")
    text = toc_features["feature_text"].dropna()
    if not all(isinstance(value, str) for value in text):
        raise ValueError("TOC feature_text must contain text or missing values.")
    for column in ["numeric_only_text", "repeated_text"]:
        values = toc_features[column]
        if not pd.api.types.is_bool_dtype(values) or values.isna().any():
            raise ValueError(f"TOC {column} must contain True or False.")


def _join_pieces(pieces, parent_asin, column):
    if isinstance(pieces, Mapping) or not pd.api.types.is_list_like(pieces, allow_sets=False):
        raise ValueError(f"Book {parent_asin}: {column} must be an ordered list or array.")
    text = []
    for position, piece in enumerate(pieces, start=1):
        if not isinstance(piece, str):
            raise ValueError(f"Book {parent_asin}: {column} piece {position} must be text.")
        if piece.strip():
            text.append(piece.strip())
    return "\n".join(text)


def _book_documents(books):
    rows = []
    for book in books.itertuples(index=False):
        features = _join_pieces(book.features, book.parent_asin, "features")
        description = _join_pieces(book.description, book.parent_asin, "description")
        source, text = ("features", features) if features else ("description", description)
        if text:
            rows.append({
                "document_id": f"{book.parent_asin}:{source}",
                "parent_asin": book.parent_asin, "book_title": book.title,
                "source": source, "text": text,
            })
    # Positions and TOC-only review flags are missing for book-level documents.
    return pd.DataFrame(rows, columns=DOCUMENT_COLUMNS)


def _toc_documents(books, toc_features):
    has_text = toc_features["feature_text"].fillna("").str.strip().ne("")
    documents = toc_features.loc[has_text, TOC_COLUMNS].copy()
    documents = documents.rename(columns={"feature_text": "text"})
    documents["document_id"] = (
        documents["parent_asin"] + ":toc:" + documents["raw_position"].astype(str)
    )
    documents["source"] = "toc"
    titles = books.set_index("parent_asin")["title"]
    documents["book_title"] = documents["parent_asin"].map(titles)
    return documents


def build_documents(books: pd.DataFrame, toc_features: pd.DataFrame) -> pd.DataFrame:
    """Return one document per nonblank TOC item and at most one book-level text.

    Book-level text joins features in saved order, falling back to description
    when features has no nonblank text. TOC text and review flags are copied;
    numeric or repeated text is retained. The two flags are missing for
    book-level rows because their definitions apply only to TOC items.

    Output order is book ID, then original TOC position, then book-level text.
    Document IDs are stable source references, not content hashes. No inputs
    are modified, files written, texts truncated, or embedding vectors created.
    The pipeline separately verifies that the TOC file matches its raw source.
    """
    _validate_books(books)
    _validate_toc(books, toc_features)
    documents = pd.concat([
        _toc_documents(books, toc_features), _book_documents(books),
    ], ignore_index=True)
    documents["document_version"] = DOCUMENT_VERSION
    documents[STRING_COLUMNS] = documents[STRING_COLUMNS].astype("string")
    documents["raw_position"] = documents["raw_position"].astype("Int64")
    for column in ["numeric_only_text", "repeated_text"]:
        documents[column] = documents[column].astype("boolean")
    return documents[DOCUMENT_COLUMNS].sort_values(
        ["parent_asin", "raw_position"], na_position="last",
    ).reset_index(drop=True)
