from __future__ import annotations

import os
import duckdb as ddb

PARQUET_GLOB = "data/parquet/statcast_regular/statcast_*.parquet"
DB_PATH = "statcast.duckdb"  # local embedded DB file


def ensure_data_exists() -> None:
    pattern_root = os.path.dirname(PARQUET_GLOB)
    if not os.path.isdir(pattern_root):
        raise SystemExit(
            f"Parquet folder not found: {pattern_root}."
            f"Run build_parquet_years(...) from data_collector.py first."
        )


def main() -> None:
    ensure_data_exists()
    con = ddb.connect(DB_PATH)

    # Macro for configurable PA threshold (change 300 → 200, etc.)
    con.execute("CREATE OR REPLACE MACRO PA_THRESHOLD() AS 300;")

    # Raw pitches view over all Parquet files
    con.execute(f"""
        CREATE OR REPLACE VIEW pitches AS
        SELECT * FROM read_parquet('{PARQUET_GLOB}');
    """)

    # One row per plate appearance = last pitch of each PA
    con.execute("""
        CREATE OR REPLACE VIEW plate_appearances AS
        WITH last_pitch AS (
            SELECT game_year, batter, game_pk, at_bat_number, MAX(pitch_number) AS last_pitch
            FROM pitches
            GROUP BY 1,2,3,4
        )
        SELECT p.*
        FROM pitches p
        JOIN last_pitch lp
          ON p.game_year=lp.game_year
         AND p.batter=lp.batter
         AND p.game_pk=lp.game_pk
         AND p.at_bat_number=lp.at_bat_number
         AND p.pitch_number=lp.last_pitch;
    """)

    # Eligible batter-year pairs by PA threshold (uses the macro)
    con.execute("""
        CREATE OR REPLACE VIEW eligible_batter_year AS
        SELECT game_year, batter, COUNT(*) AS pa_count
        FROM plate_appearances
        GROUP BY 1,2
        HAVING COUNT(*) >= PA_THRESHOLD();
    """)

    # Filtered pitches for qualified batters (join back to pitch level)
    con.execute("""
        CREATE OR REPLACE VIEW pitches_qualified AS
        SELECT p.*
        FROM pitches p
        JOIN eligible_batter_year e
          ON p.game_year = e.game_year AND p.batter = e.batter;
    """)

    # Quick sanity prints
    print("First two rows from qualified pitches:")
    print(con.execute("SELECT * FROM pitches_qualified LIMIT 2").df())

    print("Counts by year (qualified PAs):")
    print(con.execute("SELECT game_year, COUNT(*) AS rows FROM pitches_qualified GROUP BY 1 ORDER BY 1").df())


if __name__ == "__main__":
    main()