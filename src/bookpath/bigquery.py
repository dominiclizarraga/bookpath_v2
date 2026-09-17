import json
import subprocess
import pandas as pd

def load_books(project: str, dataset: str, table: str, location: str, max_rows: int = 10_000) -> pd.DataFrame:
    """Download the book table from BigQuery."""
    full_table = f"{project}.{dataset}.{table}"
    query = f"SELECT * FROM `{full_table}` ORDER BY parent_asin"

    result = subprocess.run(
        ["bq", f"--location={location}", "query", f"--max_rows={max_rows}",
        "--use_legacy_sql=false", "--format=json", query],
        capture_output=True,
        text=True,
        check=True,
    )
    return pd.DataFrame(json.loads(result.stdout))
