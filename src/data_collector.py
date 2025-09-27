"""
Data collector for MLB Statcast (regular season) with robust fetching and optional
batter-year workload filtering. Can be imported (functions) or run as a script.

Requires: pybaseball, pandas, pyarrow (for Parquet)
Optional: duckdb (used in parquet_load.py, not required here)

pip install pybaseball pandas pyarrow
"""
from __future__ import annotations

import os
import time
import math
import calendar
from datetime import date, timedelta
from typing import Optional, Sequence, List, Tuple, Set

import pandas as pd
from pybaseball import statcast, cache as pb_cache

# -----------------------------
# Column set used downstream
# -----------------------------
DESIRED_COLS: List[str] = [
    "game_year", "pitch_type", "release_speed", "player_name", "batter", "pitcher",
    "events", "description", "stand", "p_throws", "type", "bb_type",
    "balls", "strikes", "outs_when_up", "inning", "inning_topbot",
    "game_pk", "plate_x", "plate_z",
    "estimated_woba_using_speedangle", "estimated_ba_using_speedangle",
    "launch_speed_angle", "pitch_number", "at_bat_number",
]

# -----------------------------
# Robust window fetch with retries
# -----------------------------

def _fetch_window(start_str: str, end_str: str, max_retries: int = 3, pause: float = 1.0) -> pd.DataFrame:
    """Fetch a date window via pybaseball.statcast with simple retries/backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            return statcast(start_dt=start_str, end_dt=end_str)
        except Exception:  # transient CSV/parse/network hiccups
            if attempt == max_retries:
                raise
            time.sleep(pause * attempt)
    return pd.DataFrame()


def _date_str(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _split_dates(start_d: date, end_d: date, chunks: int):
    """Yield (start, end) inclusive ranges split into ~equal `chunks`."""
    total_days = (end_d - start_d).days + 1
    size = max(1, math.ceil(total_days / chunks))
    cur = start_d
    while cur <= end_d:
        nxt = min(cur + timedelta(days=size - 1), end_d)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


# -----------------------------
# Fetch a month, degrading to smaller windows on failure
# -----------------------------

def fetch_month_robust(year: int, month: int, game_type: str = "R",
                       desired_cols: Sequence[str] | None = None,
                       verbose: bool = True) -> pd.DataFrame:
    if desired_cols is None:
        desired_cols = DESIRED_COLS

    start_d = date(year, month, 1)
    end_d = date(year, month, calendar.monthrange(year, month)[1])

    # Strategy ladder: full month -> halves -> ~10-day chunks -> daily
    strategies = []
    strategies.append([(start_d, end_d)])
    mid = start_d + timedelta(days=((end_d - start_d).days // 2))
    strategies.append([(start_d, mid), (mid + timedelta(days=1), end_d)])
    strategies.append(list(_split_dates(start_d, end_d, chunks=max(1, math.ceil((end_d - start_d).days / 10)))))
    strategies.append([(start_d + timedelta(days=i), start_d + timedelta(days=i)) for i in range((end_d - start_d).days + 1)])

    frames: List[pd.DataFrame] = []
    last_err: Optional[Exception] = None

    for idx, strat in enumerate(strategies, start=1):
        if verbose:
            print(f"  Strategy {idx}: {len(strat)} window(s)")
        frames = []
        try:
            for (s, e) in strat:
                s_str, e_str = _date_str(s), _date_str(e)
                if verbose:
                    print(f"    Fetch {s_str}..{e_str}")
                df = _fetch_window(s_str, e_str, max_retries=3, pause=1.0)
                if df is None or df.empty:
                    continue
                if "game_type" not in df.columns:
                    continue
                df = df[df["game_type"] == game_type]
                if df.empty:
                    continue
                df = df.reindex(columns=desired_cols)
                frames.append(df)
            if frames:
                break
        except Exception as err:  # try finer granularity
            last_err = err
            if verbose:
                print(f"    Strategy {idx} failed: {err}")
            continue

    if not frames:
        if last_err:
            raise last_err
        return pd.DataFrame({c: pd.Series(dtype="object") for c in desired_cols})

    return pd.concat(frames, ignore_index=True)


# -----------------------------
# Public: fetch across years into a single DataFrame (optionally filter by workload)
# -----------------------------

def fetch_statcast_regular(
    start_year: int = 2015,
    end_year: int = 2024,
    columns: Optional[Sequence[str]] = None,
    game_type: str = "R",
    use_cache: bool = True,
    show_progress: bool = True,
    min_batter_pa_per_year: Optional[int] = None,
    count_official_ab: bool = False,
) -> pd.DataFrame:
    """Return a pitch-level DataFrame for regular season with optional workload filter."""
    if use_cache:
        try:
            pb_cache.enable()
        except Exception:
            pass

    desired_cols = list(columns) if columns is not None else DESIRED_COLS

    frames: List[pd.DataFrame] = []
    for yr in range(start_year, end_year + 1):
        for mo in range(3, 12):  # Mar..Nov
            if show_progress:
                print(f"[build DF] {yr}-{mo:02d}")
            df_month = fetch_month_robust(yr, mo, game_type=game_type, desired_cols=desired_cols, verbose=show_progress)
            if not df_month.empty:
                frames.append(df_month)

    if not frames:
        return pd.DataFrame({c: pd.Series(dtype="object") for c in desired_cols})

    data = pd.concat(frames, ignore_index=True)

    # Optional workload filter (>= threshold PAs or ABs per (year, batter))
    if not min_batter_pa_per_year:
        return data

    # Reduce to one row per PA (last pitch of the at-bat)
    if "pitch_number" not in data.columns:
        data["pitch_number"] = 0

    reduced = (
        data.dropna(subset=["game_year", "batter", "game_pk", "at_bat_number"]).
        sort_values(["game_year", "batter", "game_pk", "at_bat_number", "pitch_number"]).
        groupby(["game_year", "batter", "game_pk", "at_bat_number"], as_index=False).
        tail(1)
    )

    if count_official_ab:
        non_ab_events = {"walk", "intent_walk", "hit_by_pitch", "sac_fly", "sac_bunt", "catcher_interference", "catcher_interf"}
        mask_ab = ~reduced["events"].fillna("").isin(non_ab_events)
        workload = reduced.loc[mask_ab].groupby(["game_year", "batter"]).size()
    else:
        workload = reduced.groupby(["game_year", "batter"]).size()

    eligible_pairs: Set[Tuple[int, int]] = set(workload[workload >= min_batter_pa_per_year].index.tolist())

    keep_mask = data.apply(
        lambda r: (int(r.get("game_year")) if pd.notna(r.get("game_year")) else None,
                   int(r.get("batter")) if pd.notna(r.get("batter")) else None) in eligible_pairs,
        axis=1
    )
    return data.loc[keep_mask].reset_index(drop=True)


# -----------------------------
# Builder: write monthly Parquet files and resume safely
# -----------------------------

def build_parquet_years(out_dir: str,
                        start_year: int = 2015,
                        end_year: int = 2024,
                        use_cache: bool = True,
                        verbose: bool = True) -> None:
    if use_cache:
        try:
            pb_cache.enable()
        except Exception:
            pass

    os.makedirs(out_dir, exist_ok=True)

    for yr in range(start_year, end_year + 1):
        for mo in range(3, 12):  # Mar..Nov
            fname = f"statcast_{yr}_{mo:02d}.parquet"
            fpath = os.path.join(out_dir, fname)
            if os.path.exists(fpath):
                if verbose:
                    print(f"[skip] {fname} exists")
                continue
            if verbose:
                print(f"[build] {fname}")
            df_month = fetch_month_robust(yr, mo, game_type="R", desired_cols=DESIRED_COLS, verbose=verbose)
            if not df_month.empty:
                df_month.to_parquet(fpath, index=False)
                if verbose:
                    print(f"  wrote {len(df_month):,} rows → {fpath}")
            else:
                if verbose:
                    print("  empty after filtering; nothing written.")


if __name__ == "__main__":
    # Example 1: Build a single big DataFrame in memory
    #df = fetch_statcast_regular(2015, 2016, show_progress=True)  # narrow years while testing
    #print("DF shape:", df.shape)
    #print(df.head(2))

    # Example 2: Or build Parquet files you can query later (recommended for scale)
    build_parquet_years(out_dir="data/parquet/statcast_regular", start_year=2015, end_year=2024)