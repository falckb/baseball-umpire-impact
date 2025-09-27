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

    # --- Configurable PA threshold (change here to 200 later if desired) ---
    con.execute("CREATE OR REPLACE MACRO PA_THRESHOLD() AS 300;")

    # --- Zone geometry macros ---
    # Horizontal half-plate width per your spec, in feet
    con.execute("CREATE OR REPLACE MACRO PLATE_HALF_FT() AS 0.71;")
    # Baseball radius: 1.45 inches => feet
    con.execute("CREATE OR REPLACE MACRO BALL_RADIUS_FT() AS 1.45 / 12.0;")

    # TRUE_STRIKE(px, pz, sz_top, sz_bot) returns:
    #   - TRUE if any part of the ball clips the zone
    #   - FALSE if the ball fully misses the expanded zone
    #   - NULL if any inputs are NULL (unknown)
    con.execute("""
    CREATE OR REPLACE MACRO TRUE_STRIKE(px, pz, sz_top, sz_bot) AS
    CASE
      WHEN px IS NULL OR pz IS NULL OR sz_top IS NULL OR sz_bot IS NULL THEN NULL
      ELSE
        CASE
          WHEN abs(px) <= (PLATE_HALF_FT() + BALL_RADIUS_FT())
           AND pz BETWEEN LEAST(sz_bot, sz_top) - BALL_RADIUS_FT()
                      AND GREATEST(sz_bot, sz_top) + BALL_RADIUS_FT()
          THEN TRUE ELSE FALSE
        END
    END;
    """)

    # --- Base view over Parquet ---
    con.execute(f"""
        CREATE OR REPLACE VIEW pitches AS
        SELECT * FROM read_parquet('{PARQUET_GLOB}');
    """)

    # --- Augment with geometric truth + comparison vs. recorded 'type' ---
    # NOTE:
    #  - We null out the comparison on any pitch with bat_speed present (swings),
    #    on non-called results (type NOT IN ('B','S')), or when truth is unknown.
    #  - Labels:
    #       MATCH        -> geometric truth agrees with type
    #       MISS_STRIKE  -> called ball but geometric TRUE_STRIKE
    #       MISS_BALL    -> called strike but geometric not strike
    con.execute("""
        CREATE OR REPLACE VIEW pitches_with_truth AS
        SELECT
        p.*,

        -- Geometric truth flags
        TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) AS true_strike,
        CASE
            WHEN TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) IS NULL THEN NULL
            WHEN TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) THEN FALSE
            ELSE TRUE
        END AS true_ball,
        CASE
            WHEN TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) IS NULL THEN NULL
            WHEN TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) THEN 'TRUE_STRIKE'
            ELSE 'TRUE_BALL'
        END AS true_zone_label,

        -- Comparison vs recorded 'type' — evaluate ONLY on called pitches B/S.
        -- NULL when:
        --   - type NOT IN ('B','S')  (i.e., swings / contact / other)
        --   - geometric truth unknown (missing coords/zone)
        CASE
            WHEN p.type NOT IN ('B','S') THEN NULL
            WHEN TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) IS NULL THEN NULL

            -- Agreements
            WHEN p.type = 'S' AND TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) = TRUE  THEN 'MATCH'
            WHEN p.type = 'B' AND TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) = FALSE THEN 'MATCH'

            -- Disagreements
            WHEN p.type = 'S' AND TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) = FALSE THEN 'MISS_BALL'
            WHEN p.type = 'B' AND TRUE_STRIKE(p.plate_x, p.plate_z, p.sz_top, p.sz_bot) = TRUE  THEN 'MISS_STRIKE'
        END AS truth_vs_type
        FROM pitches p;
    """)

    # --- One row per plate appearance = last pitch of each PA ---
    con.execute("""
        CREATE OR REPLACE VIEW plate_appearances AS
        WITH last_pitch AS (
            SELECT game_year, batter, game_pk, at_bat_number, MAX(pitch_number) AS last_pitch
            FROM pitches_with_truth
            GROUP BY 1,2,3,4
        )
        SELECT pwt.*
        FROM pitches_with_truth pwt
        JOIN last_pitch lp
          ON pwt.game_year=lp.game_year
         AND pwt.batter=lp.batter
         AND pwt.game_pk=lp.game_pk
         AND pwt.at_bat_number=lp.at_bat_number
         AND pwt.pitch_number=lp.last_pitch;
    """)

    # --- Eligible batter-year pairs by PA threshold ---
    con.execute("""
        CREATE OR REPLACE VIEW eligible_batter_year AS
        SELECT game_year, batter, COUNT(*) AS pa_count
        FROM plate_appearances
        GROUP BY 1,2
        HAVING COUNT(*) >= PA_THRESHOLD();
    """)

    # --- Qualified pitches (inherits the new columns) ---
    con.execute("""
        CREATE OR REPLACE VIEW pitches_qualified AS
        SELECT pwt.*
        FROM pitches_with_truth pwt
        JOIN eligible_batter_year e
          ON pwt.game_year = e.game_year AND pwt.batter = e.batter;
    """)

    # Quick sanity prints
    print("First two rows from qualified pitches:")
    print(con.execute("SELECT * FROM pitches_qualified LIMIT 2").df())

    print("Counts by year (qualified PAs):")
    print(con.execute("SELECT game_year, COUNT(*) AS rows FROM pitches_qualified GROUP BY 1 ORDER BY 1").df())


if __name__ == "__main__":
    main()
