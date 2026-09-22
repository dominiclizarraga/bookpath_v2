import argparse
import json
import os
import subprocess
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from bookpath.local_data import read_books_from_parquet, save_books_to_parquet


def load_books(
    project: str, dataset: str, table: str, location: str, max_rows: int = 10_000
) -> pd.DataFrame:
    """Download up to max_rows books from BigQuery, ordered by identifier."""
    if max_rows <= 0:
        raise ValueError("max_rows must be greater than zero")
    full_table = f"{project}.{dataset}.{table}"
    query = f"SELECT * FROM `{full_table}` ORDER BY parent_asin LIMIT {max_rows}"

    try:
        result = subprocess.run(
            [
                "bq",
                f"--location={location}",
                "query",
                f"--max_rows={max_rows}",
                "--use_legacy_sql=false",
                "--format=json",
                query,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return pd.DataFrame(json.loads(result.stdout))
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or str(error)
        raise RuntimeError(f"BigQuery command failed: {message}") from error


def main(
    *, max_rows: int = 10, output_path: str | Path = "data/raw/books_sample.parquet"
) -> None:
    """Download raw books to a chosen file without replacing existing data."""
    if max_rows <= 0:
        raise ValueError("max_rows must be greater than zero")
    output_path = Path(output_path)
    if output_path.exists():
        print(f"Skipping BigQuery: {output_path} already exists. Read it locally.")
        return

    load_dotenv()

    variable_names = [
        "BOOKPATH_GCP_PROJECT",
        "BOOKPATH_BQ_DATASET",
        "BOOKPATH_BQ_TABLE",
        "BOOKPATH_BQ_LOCATION",
    ]

    missing_env = [name for name in variable_names if not os.getenv(name)]

    if missing_env:
        raise RuntimeError(f"Missing environment variables: {", ".join(missing_env)}")

    print("Downloading books from BigQuery...", flush=True)

    books = load_books(
        project=os.environ["BOOKPATH_GCP_PROJECT"],
        dataset=os.environ["BOOKPATH_BQ_DATASET"],
        table=os.environ["BOOKPATH_BQ_TABLE"],
        location=os.environ["BOOKPATH_BQ_LOCATION"],
        max_rows=max_rows,
    )
    print(f"Loaded: {len(books)} books")
    save_books_to_parquet(books, output_path)
    print(f"Saved raw books to: {output_path}")

    saved_books = read_books_from_parquet(output_path)
    print(f"Read back: {len(saved_books)} books")
    print(f"Columns: {', '.join(saved_books.columns)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download raw books to local Parquet.")
    parser.add_argument("--max-rows", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("data/raw/books_sample.parquet"))
    arguments = parser.parse_args()
    main(max_rows=arguments.max_rows, output_path=arguments.output)
