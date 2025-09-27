"""
Load Parquet files into DuckDB, define a simple view, and print the first two rows.

Requires: duckdb, pyarrow
pip install duckdb pyarrow
"""
from __future__ import annotations

import os
import duckdb as ddb

PARQUET_GLOB = "data/parquet/statcast_regular/statcast_*.parquet"
DB_PATH = "statcast.duckdb"  # local embedded DB file


def ensure_data_exists() -> None:
    pattern_root = os.path.dirname(PARQUET_GLOB)
    if not os.path.isdir(pattern_root):
        raise SystemExit(
            f"Parquet folder not found: {pattern_root}.\n"
            f"Run build_parquet_years(...) from data_collector.py first."
        )


def main() -> None:
    ensure_data_exists()
    con = ddb.connect(DB_PATH)

    # Create/replace a view over all Parquet files (partition pruning by filename is automatic)
    con.execute(f"""
        CREATE OR REPLACE VIEW pitches AS
        SELECT * FROM read_parquet('{PARQUET_GLOB}');
    """)

    # Quick sanity query: first two rows
    df_preview = con.execute("SELECT * FROM pitches LIMIT 2").df()
    print(df_preview)

    # (Optional) You can add more derived views here, e.g. one row per PA, eligible batters, etc.


if __name__ == "__main__":
    main()