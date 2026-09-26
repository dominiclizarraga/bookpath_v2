"""Build inspectable TOC text features from a saved raw book snapshot."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from bookpath.local_data import read_books_from_parquet, save_books_to_parquet


FEATURE_VERSION = "toc-v1"
TEXT_COLUMNS = [
    "parent_asin", "ol_edition_key", "book_title", "text_source", "base_text",
    "chapter_subtitle", "feature_text", "label", "level", "page", "entry_class",
    "authors_json", "description_json", "raw_item_json",
]
ENTRY_COLUMNS = TEXT_COLUMNS + ["raw_position", "subtitle_added"]


def _nonblank_text(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _choose_main_text(item):
    if isinstance(item, str):
        return _nonblank_text(item), "plain_string"
    for key in ["title", "value", "label"]:
        text = _nonblank_text(item.get(key))
        if text is not None:
            return text, key
    return None, None


def _words_for_comparison(text):
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def _combine_chapter_text(base_text, subtitle):
    """Use subtitle text once; comparison ignores case and punctuation."""
    if subtitle is None or not _words_for_comparison(subtitle):
        return base_text, False
    if base_text is None:
        return subtitle, True
    subtitle_words = f" {_words_for_comparison(subtitle)} "
    title_words = f" {_words_for_comparison(base_text)} "
    if subtitle_words in title_words:
        return base_text, False
    return f"{base_text}: {subtitle}", True


def _context_text(value):
    if value is None:
        return None
    return str(value)


def _entry_features(book, raw_position, item):
    fields = item if isinstance(item, dict) else {}
    base_text, text_source = _choose_main_text(item)
    subtitle = _nonblank_text(fields.get("subtitle"))
    feature_text, subtitle_added = _combine_chapter_text(base_text, subtitle)
    return {
        "parent_asin": book.parent_asin,
        "ol_edition_key": book.ol_edition_key,
        "book_title": book.title,
        "raw_position": raw_position,
        "text_source": text_source,
        "base_text": base_text,
        "chapter_subtitle": subtitle,
        "feature_text": feature_text,
        "subtitle_added": subtitle_added,
        "label": _context_text(fields.get("label")),
        "level": _context_text(fields.get("level")),
        "page": _context_text(fields.get("pagenum")),
        "entry_class": _context_text(fields.get("class")),
        "authors_json": json.dumps(fields.get("authors"), ensure_ascii=False),
        "description_json": json.dumps(fields.get("description"), ensure_ascii=False),
        "raw_item_json": json.dumps(item, ensure_ascii=False),
    }


def _validate_books(books):
    required = {"parent_asin", "ol_edition_key", "title", "raw_toc_json"}
    missing = required.difference(books.columns)
    if missing:
        raise ValueError(f"Missing book columns: {', '.join(sorted(missing))}")
    identifiers = books["parent_asin"]
    if not identifiers.map(lambda value: isinstance(value, str) and bool(value.strip())).all():
        raise ValueError("parent_asin must contain nonblank string identifiers.")
    if identifiers.duplicated().any():
        raise ValueError("parent_asin must be unique: one row per Amazon parent record.")


def _decode_raw_toc(book):
    try:
        raw_toc = json.loads(book.raw_toc_json)
    except (ValueError, TypeError) as error:
        raise ValueError(f"Book {book.parent_asin}: invalid raw_toc_json.") from error
    if not isinstance(raw_toc, list):
        raise ValueError(f"Book {book.parent_asin}: raw_toc_json must decode to a list.")
    return raw_toc


def _add_review_flags(features):
    features["missing_text"] = features["feature_text"].isna()
    features["numeric_only_text"] = (
        features["feature_text"].str.fullmatch(r"[0-9]+").fillna(False).astype(bool)
    )
    comparison = features[["parent_asin"]].copy()
    comparison["text"] = (
        features["feature_text"].str.casefold().str.replace(r"\s+", " ", regex=True).str.strip()
    )
    features["repeated_text"] = (
        features["feature_text"].notna() & comparison.duplicated(keep=False)
    )


def build_toc_features(books: pd.DataFrame) -> pd.DataFrame:
    """Return one row per raw TOC item, including empty and review-worthy items.

    Main text uses title, then value, then label, or a plain-string item.
    A chapter subtitle is added unless its words already appear in the main
    text, ignoring case and punctuation. A subtitle alone can supply text.
    The original item is preserved in raw_item_json. No input is modified,
    rows are not deduplicated, and this function performs no file or network IO.
    """
    _validate_books(books)
    rows = []
    for book in books.itertuples(index=False):
        for position, item in enumerate(_decode_raw_toc(book), start=1):
            if not isinstance(item, (dict, str)):
                raise ValueError(
                    f"Book {book.parent_asin}, item {position}: expected a dictionary or string."
                )
            rows.append(_entry_features(book, position, item))

    features = pd.DataFrame(rows, columns=ENTRY_COLUMNS)
    features[TEXT_COLUMNS] = features[TEXT_COLUMNS].astype("string")
    features["raw_position"] = features["raw_position"].astype("int64")
    features["subtitle_added"] = features["subtitle_added"].astype(bool)
    _add_review_flags(features)
    features["feature_version"] = FEATURE_VERSION
    return features


def _file_checksum(path):
    with path.open("rb") as raw_file:
        return hashlib.file_digest(raw_file, "sha256").hexdigest()


def prepare_toc_features(input_path: str | Path, output_path: str | Path) -> Path:
    """Read local books and save a separate, versioned TOC feature Parquet."""
    input_path, output_path = Path(input_path), Path(output_path)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Raw input and processed output must use different paths.")
    if output_path.exists():
        raise FileExistsError(f"Processed TOC file already exists: {output_path}")
    source_checksum = _file_checksum(input_path)
    features = build_toc_features(read_books_from_parquet(input_path))
    if _file_checksum(input_path) != source_checksum:
        raise RuntimeError("Raw file changed while building TOC features; nothing saved.")
    features["source_sha256"] = source_checksum
    return save_books_to_parquet(features, output_path)


def main():
    parser = argparse.ArgumentParser(description="Build TOC features from local Parquet.")
    parser.add_argument("--input", default="data/raw/books.parquet")
    parser.add_argument("--output", default="data/processed/toc_features.parquet")
    arguments = parser.parse_args()
    output_path = prepare_toc_features(arguments.input, arguments.output)
    print(f"Saved TOC features to {output_path}")


if __name__ == "__main__":
    main()
