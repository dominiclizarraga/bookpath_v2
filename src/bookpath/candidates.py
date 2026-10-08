"""Collect TF-IDF candidates for reviewed queries without changing baseline 0."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd
import sklearn

from bookpath.local_data import read_books_from_parquet, save_books_to_parquet
from bookpath.tfidf import build_book_corpus, rank_books


def build_candidates(documents, queries, top_k=10):
    """Return every book rank per query and a top-k review list with no labels.

    Background and success criteria stay visible as judgment context; only
    the exact query text is passed to the unchanged baseline implementation.
    """
    if not queries or not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("Supply at least one query and a positive integer top_k.")
    for record in queries:
        for field in ["query_id", "query"]:
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Every query requires nonblank {field}.")
    identifiers = [record["query_id"] for record in queries]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Query IDs must be unique.")
    corpus = build_book_corpus(documents)
    rankings, candidates = [], []
    for record in queries:
        ranking, _ = rank_books(corpus, record["query"])
        candidates.append({**record, "books": ranking.head(top_k).to_dict(orient="records")})
        ranking.insert(0, "query_id", record["query_id"])
        rankings.append(ranking)
    return pd.concat(rankings, ignore_index=True), candidates


def _checksum(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def prepare_candidates(documents_path, queries_path, output_dir):
    """Save a new review run, protecting existing files and recording inputs."""
    documents_path, queries_path, output_dir = map(Path, [documents_path, queries_path, output_dir])
    if output_dir.exists():
        raise FileExistsError(f"Candidate output already exists: {output_dir}")
    checksums = {path: _checksum(path) for path in [documents_path, queries_path]}
    query_set = json.loads(queries_path.read_text())
    documents = read_books_from_parquet(documents_path)
    rankings, candidates = build_candidates(documents, query_set["queries"])
    if any(_checksum(path) != checksum for path, checksum in checksums.items()):
        raise RuntimeError("A candidate input changed during retrieval; nothing saved.")
    metadata = {
        "method": "baseline_0_tfidf_cosine",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "query_set_version": query_set["version"],
        "queries_sha256": checksums[queries_path],
        "documents_sha256": checksums[documents_path],
        "query_count": len(candidates),
        "candidate_books_per_query": documents["parent_asin"].nunique(),
        "full_ranking_rows": len(rankings),
        "top_k": 10,
        "review_pairs": sum(len(record["books"]) for record in candidates),
        "scikit_learn_version": sklearn.__version__,
        "code_sha256": {
            name: _checksum(Path(__file__).with_name(name))
            for name in ["tfidf.py", "candidates.py"]
        },
        "retrieval_input": "query text only; background and success criterion are judgment context",
        "labels_status": "No relevance labels assigned; TF-IDF candidates only, not a complete pool.",
        "queries": candidates,
    }
    output_dir.mkdir(parents=True)
    save_books_to_parquet(rankings, output_dir / "rankings.parquet")
    (output_dir / "candidates.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Show baseline TF-IDF candidates for all draft queries.")
    parser.add_argument("--input", type=Path, default=Path("data/processed/documents.parquet"))
    parser.add_argument("--queries", type=Path, default=Path("benchmarks/gold_v1/queries.json"))
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/gold_v1_tfidf"))
    arguments = parser.parse_args()
    output = prepare_candidates(arguments.input, arguments.queries, arguments.output)
    print(f"Saved all book rankings and top-ten review candidates to {output}")


if __name__ == "__main__":
    main()
