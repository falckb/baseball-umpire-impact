from typing import Optional, Sequence, List
import calendar
import pandas as pd
from pybaseball import statcast, cache as pb_cache

def fetch_statcast_regular(
    start_year: int = 2015,
    end_year: int = 2024,
    columns: Optional[Sequence[str]] = None,
    game_type: str = "R",
    use_cache: bool = True,
    show_progress: bool = True,
) -> pd.DataFrame:
    """
    Fetch Statcast pitch-by-pitch data for MLB regular-season (or other game_type) games
    over a range of years, filtered to selected columns, returned as one DataFrame.

    Parameters
    ----------
    start_year : int
        First season to include (inclusive).
    end_year : int
        Last season to include (inclusive).
    columns : Sequence[str] | None
        Columns to keep. If None, uses a default set tailored for your Markov chain work.
    game_type : str
        MLB game type code, default 'R' (regular season). Others: 'S' (spring), 'E' (exhib), 'F' (wild card),
        'D' (Division), 'L' (LCS), 'W' (World Series), etc.
    use_cache : bool
        Enable pybaseball cache to speed up repeated calls.
    show_progress : bool
        Print year/month progress while fetching.

    Returns
    -------
    pd.DataFrame
    """

    if use_cache:
        try:
            pb_cache.enable()
        except Exception:
            # Cache enabling is best-effort; proceed even if it fails.
            pass

    default_cols: List[str] = [
        "game_year", "pitch_type", "release_speed", "player_name", "batter", "pitcher",
        "events", "description", "stand", "p_throws", "type", "bb_type",
        "balls", "strikes", "outs_when_up", "inning", "inning_topbot",
        "game_pk", "plate_x", "plate_z",
        "estimated_woba_using_speedangle", "estimated_ba_using_speedangle",
        "launch_speed_angle", "pitch_number", "at_bat_number",
    ]
    desired_cols: List[str] = list(columns) if columns is not None else default_cols

    frames: List[pd.DataFrame] = []

    for year in range(start_year, end_year + 1):
        # Regular season generally lives Mar–Nov; querying those months avoids many empty pulls.
        for month in range(3, 12):  # 3..11 inclusive
            start = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            end = f"{year}-{month:02d}-{last_day:02d}"

            if show_progress:
                print(f"Fetching {start} to {end} ...", flush=True)

            df = statcast(start_dt=start, end_dt=end)

            if df is None or df.empty:
                continue
            if "game_type" not in df.columns:
                # If game_type is absent (rare for 2015+), skip this chunk to preserve correctness.
                continue

            # Keep only the requested game type (default: Regular season)
            df = df[df["game_type"] == game_type]
            if df.empty:
                continue

            # Ensure the DataFrame has exactly the desired columns (missing ones become NaN)
            df = df.reindex(columns=desired_cols)
            frames.append(df)

    if not frames:
        # Return an empty DF with the correct columns and object dtype to appease static type checkers
        return pd.DataFrame({c: pd.Series(dtype="object") for c in desired_cols})

    return pd.concat(frames, ignore_index=True)
