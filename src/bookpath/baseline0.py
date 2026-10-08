"""Run baseline 0 once and record its cosine ranking and exact configuration."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import sklearn

from bookpath.local_data import read_books_from_parquet, save_books_to_parquet
from bookpath.tfidf import build_book_corpus, rank_books


def _checksum(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def run_baseline(documents_path: Path, query_path: Path, output_dir: Path) -> Path:
    """Read local inputs and save a complete ranking to a new directory."""
    documents_path, query_path, output_dir = map(Path, [documents_path, query_path, output_dir])
    if output_dir.exists():
        raise FileExistsError(f"Baseline output already exists: {output_dir}")
    input_checksums = {path: _checksum(path) for path in [documents_path, query_path]}
    query_record = json.loads(query_path.read_text())
    for field in ["query_id", "query"]:
        value = query_record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Query file requires nonblank {field}.")
    documents = read_books_from_parquet(documents_path)
    corpus = build_book_corpus(documents)
    ranking, details = rank_books(corpus, query_record["query"])
    if any(_checksum(path) != checksum for path, checksum in input_checksums.items()):
        raise RuntimeError("A baseline input changed during retrieval; nothing saved.")
    metadata = {
        "method": "baseline_0_tfidf_cosine",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **query_record,
        "documents_sha256": input_checksums[documents_path],
        "query_file_sha256": input_checksums[query_path],
        "input_document_rows": len(documents),
        "candidate_books": len(corpus),
        "ranked_books": len(ranking),
        "book_text": "Prepared document texts joined in saved order; title is metadata only.",
        "tie_break": "parent_asin ascending",
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
        "code_sha256": {
            name: _checksum(Path(__file__).with_name(name))
            for name in ["tfidf.py", "baseline0.py"]
        },
        "random_seed": None,
        "tuned": False,
        **details,
        "metrics": {name: None for name in ["nDCG@5", "Recall@10", "MRR", "Precision@5"]},
        "metric_status": "Unmeasured: no independent relevance judgments supplied.",
        "top_10": ranking.head(10).to_dict(orient="records"),
    }
    output_dir.mkdir(parents=True)
    save_books_to_parquet(ranking, output_dir / "ranking.parquet")
    (output_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Run untuned TF-IDF plus cosine baseline 0.")
    parser.add_argument("--input", type=Path, default=Path("data/processed/documents.parquet"))
    parser.add_argument("--query-file", type=Path, default=Path("benchmarks/baseline_0/query.json"))
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/baseline_0"))
    arguments = parser.parse_args()
    output = run_baseline(arguments.input, arguments.query_file, arguments.output)
    print(f"Saved complete cosine ranking and run metadata to {output}")


if __name__ == "__main__":
    main()
