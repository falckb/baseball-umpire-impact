from pybaseball import statcast
import pandas as pd

# Years you want
years = list(range(2015, 2025))

# Columns you care about
cols = [
    "game_year", "pitch_type", "release_speed", "player_name", "batter", "pitcher",
    "events", "description", "stand", "p_throw", "type", "bb_type",
    "ball", "strike", "outs_when_up", "inning", "inning_topbot",
    "game_pk", "plate_x", "plate_z",
    "estimated_woba_using_speedangle", "estimated_ba_using_speedangle",
    "launch_speed_angle", "pitch_number"
]

all_data = []

for year in years:
    print(f"Pulling {year}...")
    # Get the full season for the year
    df = statcast(start_dt=f"{year}-03-01", end_dt=f"{year}-11-30")
    
    # Filter regular season
    df = df[df["game_type"] == "R"]
    
    # Keep only your columns
    df = df[cols]
    
    all_data.append(df)

# Combine all years
final_df = pd.concat(all_data, ignore_index=True)

# Save to Excel (optional — but CSV is usually safer for big data)
final_df.to_csv("statcast_2015_2024_regular.csv", index=False)
