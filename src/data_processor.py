"""
Data Processor for Baseball Umpire Impact Analysis
Cleans and structures raw Statcast data for umpire call analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

class StatcastProcessor:
    """Process raw Statcast data for umpire call analysis"""
    
    def __init__(self, raw_data_dir: str = "data/raw", 
                 processed_data_dir: str = "data/processed"):
        self.raw_data_dir = Path(raw_data_dir)
        self.processed_data_dir = Path(processed_data_dir)
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Strike zone boundaries (approximate)
        self.strike_zone = {
            'left': -0.83,    # Left edge in feet
            'right': 0.83,    # Right edge in feet
            'top': 3.5,       # Top varies by batter, this is approximate
            'bottom': 1.5     # Bottom varies by batter
        }
    
    def load_raw_data(self, filename: str) -> pd.DataFrame:
        """Load raw Statcast CSV data"""
        filepath = self.raw_data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        df = pd.read_csv(filepath)
        self.logger.info(f"Loaded {len(df)} rows from {filename}")
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare the raw Statcast data"""
        # Create a copy to avoid modifying original
        clean_df = df.copy()
        
        # Convert date column
        clean_df['game_date'] = pd.to_datetime(clean_df['game_date'])
        
        # Filter for relevant pitch types (balls and called strikes)
        clean_df = clean_df[clean_df['type'].isin(['B', 'S'])].copy()
        
        # Filter for called strikes/balls (not swings)
        clean_df = clean_df[clean_df['description'].isin([
            'called_strike', 'ball', 'blocked_ball'
        ])].copy()
        
        # Remove rows with missing critical data
        required_columns = ['plate_x', 'plate_z', 'sz_top', 'sz_bot', 
                          'batter', 'balls', 'strikes', 'description']
        clean_df = clean_df.dropna(subset=required_columns)
        
        # Filter for minimum plate appearances (will be applied later)
        self.logger.info(f"After cleaning: {len(clean_df)} pitch records")
        
        return clean_df
    
    def determine_correct_call(self, df: pd.DataFrame) -> pd.DataFrame:
        """Determine if each pitch call was correct based on strike zone"""
        result_df = df.copy()
        
        # Determine if pitch was actually in strike zone
        result_df['in_zone'] = (
            (result_df['plate_x'] >= self.strike_zone['left']) &
            (result_df['plate_x'] <= self.strike_zone['right']) &
            (result_df['plate_z'] >= result_df['sz_bot']) &
            (result_df['plate_z'] <= result_df['sz_top'])
        )
        
        # Determine if call was correct
        conditions = [
            (result_df['description'] == 'called_strike') & (result_df['in_zone']),
            (result_df['description'].isin(['ball', 'blocked_ball'])) & (~result_df['in_zone'])
        ]
        
        result_df['correct_call'] = np.select(conditions, [True, True], default=False)
        
        # Determine if incorrect call favored batter or pitcher
        result_df['call_favors_batter'] = np.where(
            ~result_df['correct_call'],
            np.where(
                (result_df['description'] == 'called_strike') & (~result_df['in_zone']),
                False,  # Incorrect strike call favors pitcher
                True    # Incorrect ball call favors batter
            ),
            np.nan  # Correct calls don't favor anyone
        )
        
        return result_df
    
    def create_plate_appearance_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """Group pitches by plate appearance and calculate PA-level metrics"""
        # Sort by game, inning, batter, and pitch sequence
        df_sorted = df.sort_values([
            'game_date', 'batter', 'inning', 'at_bat_number', 'pitch_number'
        ])
        
        # Create plate appearance ID
        df_sorted['pa_id'] = (
            df_sorted['game_date'].astype(str) + '_' +
            df_sorted['batter'].astype(str) + '_' +
            df_sorted['at_bat_number'].astype(str)
        )
        
        return df_sorted
    
    def calculate_pa_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate plate appearance level metrics"""
        pa_metrics = []
        
        for pa_id, pa_group in df.groupby('pa_id'):
            pa_data = pa_group.sort_values('pitch_number')
            
            # Basic PA info
            pa_info = {
                'pa_id': pa_id,
                'batter': pa_data.iloc[0]['batter'],
                'game_date': pa_data.iloc[0]['game_date'],
                'pitcher': pa_data.iloc[0]['pitcher'],
                'inning': pa_data.iloc[0]['inning'],
                'events': pa_data.iloc[-1].get('events', ''),  # Final outcome
                'woba_value': pa_data.iloc[-1].get('woba_value', np.nan),
                'estimated_woba_using_speedangle': pa_data.iloc[-1].get('estimated_woba_using_speedangle', np.nan)
            }
            
            # Calculate incorrect call metrics for this PA
            incorrect_calls = pa_data[~pa_data['correct_call']]
            
            pa_info.update({
                'total_pitches': len(pa_data),
                'total_incorrect_calls': len(incorrect_calls),
                'incorrect_calls_favoring_batter': len(incorrect_calls[incorrect_calls['call_favors_batter'] == True]),
                'incorrect_calls_favoring_pitcher': len(incorrect_calls[incorrect_calls['call_favors_batter'] == False])
            })
            
            # For each incorrect call, track the count and prior incorrect calls
            incorrect_call_details = []
            for idx, pitch in pa_data.iterrows():
                if not pitch['correct_call']:
                    # Count incorrect calls before this pitch in the same PA
                    prior_incorrect = len(pa_data[
                        (pa_data['pitch_number'] < pitch['pitch_number']) & 
                        (~pa_data['correct_call'])
                    ])
                    
                    incorrect_call_details.append({
                        'pitch_number': pitch['pitch_number'],
                        'balls': pitch['balls'],
                        'strikes': pitch['strikes'],
                        'favors_batter': pitch['call_favors_batter'],
                        'prior_incorrect_calls': prior_incorrect,
                        'description': pitch['description'],
                        'in_zone': pitch['in_zone']
                    })
            
            pa_info['incorrect_call_details'] = incorrect_call_details
            pa_metrics.append(pa_info)
        
        return pd.DataFrame(pa_metrics)
    
    def filter_qualified_batters(self, pa_df: pd.DataFrame, 
                                min_pa: int = 300) -> pd.DataFrame:
        """Filter for batters with minimum plate appearances"""
        pa_counts = pa_df['batter'].value_counts()
        qualified_batters = pa_counts[pa_counts >= min_pa].index
        
        filtered_df = pa_df[pa_df['batter'].isin(qualified_batters)].copy()
        
        self.logger.info(f"Qualified batters ({min_pa}+ PA): {len(qualified_batters)}")
        self.logger.info(f"Plate appearances after filtering: {len(filtered_df)}")
        
        return filtered_df
    
    def process_full_dataset(self, raw_filename: str, 
                           output_filename: Optional[str] = None) -> pd.DataFrame:
        """Complete processing pipeline"""
        # Load and clean raw data
        raw_df = self.load_raw_data(raw_filename)
        clean_df = self.clean_data(raw_df)
        
        # Determine correct calls
        calls_df = self.determine_correct_call(clean_df)
        
        # Group by plate appearances
        pa_grouped_df = self.create_plate_appearance_groups(calls_df)
        
        # Calculate PA-level metrics
        pa_metrics_df = self.calculate_pa_metrics(pa_grouped_df)
        
        # Filter for qualified batters
        final_df = self.filter_qualified_batters(pa_metrics_df)
        
        # Save processed data
        if output_filename is None:
            output_filename = raw_filename.replace('_raw.csv', '_processed.csv')
        
        output_path = self.processed_data_dir / output_filename
        final_df.to_csv(output_path, index=False)
        
        self.logger.info(f"Saved processed data to {output_path}")
        
        return final_df

if __name__ == "__main__":
    processor = StatcastProcessor()
    
    # Example usage
    processed_df = processor.process_full_dataset("statcast_2024_raw.csv")
    print(f"Processed {len(processed_df)} plate appearances")