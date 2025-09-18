"""
Baseball Savant Data Collector
Handles API calls and raw data collection from Baseball Savant/Statcast
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from pathlib import Path
import io

class BaseballSavantCollector:
    """Collects pitch-by-pitch data from Baseball Savant/Statcast API"""
    
    def __init__(self, data_dir: str = "data/raw"):
        self.base_url = "https://baseballsavant.mlb.com/statcast_search/csv"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def get_statcast_data(self, start_date: str, end_date: str, 
                         team: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch Statcast data for a date range
        
        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format  
            team: Optional team abbreviation (e.g., 'NYY')
        
        Returns:
            DataFrame with pitch-by-pitch data
        """
        params = {
            'hfPT': '',
            'hfAB': '',
            'hfBBT': '',
            'hfPR': '',
            'hfZ': '',
            'stadium': '',
            'hfBBL': '',
            'hfNewZones': '',
            'hfGT': 'R%7C',
            'hfC': '',
            'hfSea': '',
            'hfSit': '',
            'player_type': 'batter',
            'hfOuts': '',
            'opponent': '',
            'pitcher_throws': '',
            'batter_stands': '',
            'hfSA': '',
            'game_date_gt': start_date,
            'game_date_lt': end_date,
            'team': team or '',
            'position': '',
            'hfRO': '',
            'home_road': '',
            'hfFlag': '',
            'hfPull': '',
            'metric_1': '',
            'hfInn': '',
            'min_pitches': '0',
            'min_results': '0',
            'group_by': 'name',
            'sort_col': 'pitches',
            'player_event_sort': 'h_launch_speed',
            'sort_order': 'desc',
            'min_abs': '0',
            'type': 'details'
        }
        
        try:
            self.logger.info(f"Fetching data from {start_date} to {end_date}")
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse CSV response
            df = pd.read_csv(io.StringIO(response.text))
            self.logger.info(f"Retrieved {len(df)} pitch records")
            
            return df
            
        except requests.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            raise
        except pd.errors.EmptyDataError:
            self.logger.warning("No data returned for the specified date range")
            return pd.DataFrame()
    
    def collect_season_data(self, year: int, chunk_days: int = 7) -> pd.DataFrame:
        """
        Collect full season data in chunks to avoid API limits
        
        Args:
            year: Season year
            chunk_days: Number of days per API call
            
        Returns:
            Combined DataFrame for the season
        """
        start_date = datetime(year, 3, 20)  # Approximate season start
        end_date = datetime(year, 11, 1)    # Approximate season end
        
        all_data = []
        current_date = start_date
        
        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=chunk_days), end_date)
            
            chunk_data = self.get_statcast_data(
                current_date.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d')
            )
            
            if not chunk_data.empty:
                all_data.append(chunk_data)
            
            # Be respectful to the API
            time.sleep(1)
            current_date = chunk_end + timedelta(days=1)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Save raw data
            filename = f"statcast_{year}_raw.csv"
            filepath = self.data_dir / filename
            combined_df.to_csv(filepath, index=False)
            self.logger.info(f"Saved {len(combined_df)} records to {filepath}")
            
            return combined_df
        else:
            return pd.DataFrame()
    
    def get_player_data(self, player_id: int, year: int) -> pd.DataFrame:
        """Get all pitch data for a specific player in a season"""
        params = {
            'hfPT': '',
            'hfAB': '',
            'hfBBT': '',
            'hfPR': '',
            'hfZ': '',
            'stadium': '',
            'hfBBL': '',
            'hfNewZones': '',
            'hfGT': 'R%7C',
            'hfC': '',
            'hfSea': str(year),
            'hfSit': '',
            'player_type': 'batter',
            'hfOuts': '',
            'opponent': '',
            'pitcher_throws': '',
            'batter_stands': '',
            'hfSA': '',
            'game_date_gt': f'{year}-03-01',
            'game_date_lt': f'{year}-11-30',
            'team': '',
            'position': '',
            'hfRO': '',
            'home_road': '',
            'hfFlag': '',
            'hfPull': '',
            'metric_1': '',
            'hfInn': '',
            'min_pitches': '0',
            'min_results': '0',
            'group_by': 'name',
            'sort_col': 'pitches',
            'player_event_sort': 'h_launch_speed',
            'sort_order': 'desc',
            'min_abs': '0',
            'batters_lookup[]': str(player_id),
            'type': 'details'
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return pd.read_csv(io.StringIO(response.text))
        except Exception as e:
            self.logger.error(f"Failed to get data for player {player_id}: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    collector = BaseballSavantCollector()
    
    # Example: collect recent data
    df = collector.collect_season_data(2024, chunk_days=14)
    print(f"Collected {len(df)} pitch records")