A lightweight pipeline to pull MLB Statcast pitch-by-pitch data, store it as Parquet, and query it with DuckDB for Markov-chain analysis (batter counts, called vs. “true” zone outcomes, etc.).

File structure
.
├─ src/
│  ├─ data_collector.py   # pulls Statcast (pybaseball) and writes monthly Parquet
│  ├─ pq_view_def.py      # creates DuckDB views, PA threshold macro, truth columns
│  └─ duckdb_load.py      # (optional) smoke-test: creates basic pitches view & previews
├─ data/
│  ├─ .gitkeep            # keeps the data folder in Git without large files
│  └─ parquet/
│     └─ statcast_regular/
│        └─ statcast_YYYY_MM.parquet
├─ statcast.duckdb        # local embedded DuckDB database (ignored by Git)
├─ requirements.txt
└─ .gitignore

What the views do

pitches: All Parquet rows (raw pitch level).

pitches_with_truth: Adds geometric strike-zone logic:

true_strike/true_ball and a truth_vs_type label:

MATCH, MISS_STRIKE (called ball but true strike), MISS_BALL (called strike but true ball).

Plate half-width = 0.71 ft; collision expanded by baseball radius = 1.45 in.

plate_appearances: Last pitch per PA.

eligible_batter_year: (year, batter) with ≥ PA threshold (macro defaults to 300).

pitches_qualified: Pitch rows for eligible (year, batter) pairs; includes truth columns.

One-time setup (Windows PowerShell)
# From repo root
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt


Make sure .gitignore excludes data/parquet/ and statcast.duckdb and that data/.gitkeep exists.

Refresh workflow (the usual cycle)

Use this when you want updated data but no schema changes.

.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD"

# C) Rebuild Parquet (uses pybaseball cache under the hood)
python -c "from src.data_collector import build_parquet_years; build_parquet_years('data/parquet/statcast_regular', 2018   , 2025)"

# D) Create DuckDB views and print a preview
python .\src\pq_view_def.py


(Optional) Smoke test the raw Parquet view:

python .\src\duckdb_load.py

Full reset (when schemas change)

Use this after adding columns (e.g., sz_top, sz_bot) or changing view logic.

# A) Hard clean (removes DB and Parquet)
Remove-Item -Force .\statcast.duckdb -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\data\parquet\statcast_regular -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path .\data\parquet\statcast_regular | Out-Null

# B) Reactivate env & set module path
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD"

# C) Rebuild Parquet
python -c "from src.data_collector import build_parquet_years; build_parquet_years('data/parquet/statcast_regular', 2015, 2024)"

# D) Recreate views
python .\src\pq_view_def.py

Changing the PA threshold

The PA filter is a DuckDB macro in src/pq_view_def.py:

CREATE OR REPLACE MACRO PA_THRESHOLD() AS 300;  -- change to 200 if desired


Edit it, then rerun:

python .\src\pq_view_def.py

Git hygiene

Large artifacts are ignored:

data/parquet/ (all .parquet files)

statcast.duckdb (local DB)

To keep the folder but not the data, track data/.gitkeep.

If you accidentally committed data in the past:

git rm -r --cached data\parquet statcast.duckdb
git commit -m "Stop tracking Parquet/DuckDB; keep data/.gitkeep"

Quick queries to try (after views are created)

Agreement rate on called pitches by year:

SELECT
  game_year,
  SUM(CASE WHEN truth_vs_type='MATCH' THEN 1 ELSE 0 END)::DOUBLE
  / NULLIF(SUM(CASE WHEN truth_vs_type IS NOT NULL THEN 1 ELSE 0 END), 0) AS agree_rate
FROM pitches_qualified
GROUP BY 1
ORDER BY 1;


Confusion counts:

SELECT truth_vs_type, COUNT(*) AS n
FROM pitches_qualified
WHERE truth_vs_type IS NOT NULL
GROUP BY 1
ORDER BY n DESC;

Notes

pybaseball fetches Statcast CSVs and benefits from its internal cache; running the same months again is faster.

If a pitch lacks plate_x/plate_z/sz_top/sz_bot, truth flags are NULL (unknown).

“Swings/contact” aren’t evaluated in truth_vs_type (we restrict to type IN ('B','S')).