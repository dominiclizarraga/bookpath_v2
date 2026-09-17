import json
import os
import subprocess

import pandas as pd
from dotenv import load_dotenv


def load_books(
    project: str, dataset: str, table: str, location: str, max_rows: int = 10_000
) -> pd.DataFrame:
    """Download the book table from BigQuery."""
    full_table = f"{project}.{dataset}.{table}"
    query = f"SELECT * FROM `{full_table}` ORDER BY parent_asin"

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


def main() -> None:
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
        max_rows=10,
    )
    print(f"Loaded: {len(books)} books")


if __name__ == "__main__":
    main()
