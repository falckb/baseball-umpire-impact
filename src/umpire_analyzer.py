"""
Umpire Impact Analyzer - Psychological Impact Edition
Analyzes how incorrect umpire calls affect subsequent batter performance
Focus: Identifying undervalued players who would improve with automated umpiring
File location: src/umpire_analyzer.py
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
import logging
from pathlib import Path
import json
from scipy import stats

class UmpireImpactAnalyzer:
    """Analyze psychological impact of incorrect umpire calls on batter performance"""
    
    def __init__(self, processed_data_dir: str = "data/processed",
                 reports_dir: str = "reports"):
        self.processed_data_dir = Path(processed_data_dir)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_processed_data(self, filename: str) -> pd.DataFrame:
        """Load processed plate appearance data"""
        filepath = self.processed_data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        df = pd.read_csv(filepath)
        
        # Convert string representation of lists back to actual lists
        df['incorrect_call_details'] = df['incorrect_call_details'].apply(
            lambda x: eval(x) if pd.notna(x) and x != '[]' else []
        )
        
        self.logger.info(f"Loaded {len(df)} plate appearances")
        return df
    
    def analyze_post_call_performance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze how batters perform after experiencing incorrect calls
        Key insight: Some players get rattled, others stay focused
        """
        # Expand data to have one row per incorrect call with context
        call_impact_data = []
        
        for _, pa in df.iterrows():
            if not pa['incorrect_call_details']:  # Skip PAs with no incorrect calls
                continue
                
            for call_detail in pa['incorrect_call_details']:
                # Only analyze calls that went against the batter
                if call_detail['favors_batter']:
                    continue
                    
                call_record = {
                    'batter': pa['batter'],
                    'pa_id': pa['pa_id'],
                    'game_date': pa['game_date'],
                    'current_pa_xwoba': pa['estimated_woba_using_speedangle'],
                    'current_pa_woba': pa['woba_value'],
                    'pitch_number_of_bad_call': call_detail['pitch_number'],
                    'balls_at_bad_call': call_detail['balls'],
                    'strikes_at_bad_call': call_detail['strikes'],
                    'prior_incorrect_in_pa': call_detail['prior_incorrect_calls'],
                    'bad_call_type': call_detail['description'],  # 'called_strike' or 'ball'
                    'was_strike_called_ball': call_detail['description'] == 'ball' and not call_detail['in_zone'],
                    'was_ball_called_strike': call_detail['description'] == 'called_strike' and call_detail['in_zone']
                }
                call_impact_data.append(call_record)
        
        calls_df = pd.DataFrame(call_impact_data)
        
        if calls_df.empty:
            self.logger.warning("No incorrect calls against batters found")
            return pd.DataFrame()
        
        # Sort by batter and date to analyze temporal patterns
        calls_df = calls_df.sort_values(['batter', 'game_date', 'pa_id'])
        
        return calls_df
    
    def calculate_baseline_performance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate each batter's baseline performance without bad calls"""
        
        # Get PAs with no incorrect calls against the batter
        clean_pas = []
        for _, pa in df.iterrows():
            bad_calls_against = [call for call in pa['incorrect_call_details'] 
                               if not call.get('favors_batter', True)]
            if not bad_calls_against:
                clean_pas.append(pa)
        
        if not clean_pas:
            self.logger.warning("No clean PAs found")
            return pd.DataFrame()
            
        clean_df = pd.DataFrame(clean_pas)
        
        # Calculate baseline metrics for each batter
        baseline_stats = clean_df.groupby('batter').agg({
            'woba_value': ['mean', 'std', 'count'],
            'estimated_woba_using_speedangle': ['mean', 'std', 'count']
        }).round(4)
        
        baseline_stats.columns = [
            'baseline_woba_mean', 'baseline_woba_std', 'clean_pa_count',
            'baseline_xwoba_mean', 'baseline_xwoba_std', 'baseline_xwoba_count'
        ]
        
        baseline_stats = baseline_stats.reset_index()
        
        # Filter for batters with sufficient clean PAs for reliable baseline
        baseline_stats = baseline_stats[baseline_stats['clean_pa_count'] >= 50].copy()
        
        return baseline_stats
    
    def analyze_performance_after_bad_calls(self, df: pd.DataFrame, 
                                          calls_df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze how performance changes after experiencing bad calls
        Focus on next few PAs after a bad call experience
        """
        
        # Sort data chronologically
        df_sorted = df.sort_values(['batter', 'game_date', 'pa_id']).copy()
        calls_sorted = calls_df.sort_values(['batter', 'game_date', 'pa_id']).copy()
        
        # For each bad call, find the next N plate appearances
        impact_analysis = []
        
        for _, bad_call in calls_sorted.iterrows():
            batter_id = bad_call['batter']
            bad_call_date = bad_call['game_date']
            bad_call_pa_id = bad_call['pa_id']
            
            # Get all subsequent PAs for this batter
            subsequent_pas = df_sorted[
                (df_sorted['batter'] == batter_id) & 
                (df_sorted['game_date'] >= bad_call_date) & 
                (df_sorted['pa_id'] > bad_call_pa_id)
            ].head(10)  # Look at next 10 PAs max
            
            for idx, next_pa in subsequent_pas.iterrows():
                pas_after_bad_call = len(df_sorted[
                    (df_sorted['batter'] == batter_id) & 
                    (df_sorted['game_date'] >= bad_call_date) & 
                    (df_sorted['pa_id'] > bad_call_pa_id) & 
                    (df_sorted['pa_id'] <= next_pa['pa_id'])
                ])
                
                impact_record = {
                    'batter': batter_id,
                    'bad_call_pa_id': bad_call_pa_id,
                    'bad_call_date': bad_call_date,
                    'bad_call_type': bad_call['bad_call_type'],
                    'subsequent_pa_id': next_pa['pa_id'],
                    'subsequent_pa_date': next_pa['game_date'],
                    'pas_after_bad_call': pas_after_bad_call,
                    'subsequent_woba': next_pa['woba_value'],
                    'subsequent_xwoba': next_pa['estimated_woba_using_speedangle'],
                    'days_since_bad_call': (pd.to_datetime(next_pa['game_date']) - 
                                          pd.to_datetime(bad_call_date)).days
                }
                impact_analysis.append(impact_record)
        
        return pd.DataFrame(impact_analysis)
    
    def calculate_psychological_impact_scores(self, baseline_df: pd.DataFrame,
                                           impact_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate how much each batter's performance is hurt by bad calls
        This is the key metric for identifying undervalued players
        """
        
        if baseline_df.empty or impact_df.empty:
            return pd.DataFrame()
        
        # Calculate performance after bad calls for each batter
        post_bad_call_performance = impact_df.groupby('batter').agg({
            'subsequent_woba': ['mean', 'std', 'count'],
            'subsequent_xwoba': ['mean', 'std', 'count'],
            'pas_after_bad_call': 'mean',  # Average position in sequence
            'days_since_bad_call': 'mean'
        }).round(4)
        
        post_bad_call_performance.columns = [
            'post_bad_call_woba_mean', 'post_bad_call_woba_std', 'post_bad_call_count',
            'post_bad_call_xwoba_mean', 'post_bad_call_xwoba_std', 'post_bad_call_xwoba_count',
            'avg_sequence_position', 'avg_days_gap'
        ]
        
        post_bad_call_performance = post_bad_call_performance.reset_index()
        
        # Merge with baseline performance
        merged_df = baseline_df.merge(post_bad_call_performance, on='batter', how='inner')
        
        # Calculate the psychological impact
        merged_df['woba_decline_after_bad_calls'] = (
            merged_df['baseline_woba_mean'] - merged_df['post_bad_call_woba_mean']
        )
        
        merged_df['xwoba_decline_after_bad_calls'] = (
            merged_df['baseline_xwoba_mean'] - merged_df['post_bad_call_xwoba_mean']
        )
        
        # Statistical significance test
        def calculate_significance(row):
            if row['clean_pa_count'] < 50 or row['post_bad_call_count'] < 20:
                return np.nan
                
            # Simple t-test approximation
            pooled_std = np.sqrt((row['baseline_woba_std']**2 + row['post_bad_call_woba_std']**2) / 2)
            if pooled_std == 0:
                return np.nan
                
            t_stat = row['woba_decline_after_bad_calls'] / (pooled_std * np.sqrt(2/row['clean_pa_count']))
            return abs(t_stat)
        
        merged_df['significance_score'] = merged_df.apply(calculate_significance, axis=1)
        
        # Calculate potential xwOBA improvement (the key scouting metric)
        # This estimates how much better their season xwOBA would be with robo-umps
        
        # Count total bad calls experienced
        bad_call_counts = impact_df.groupby('batter')['bad_call_pa_id'].nunique().reset_index()
        bad_call_counts.columns = ['batter', 'total_bad_calls_experienced']
        
        # Get total PAs for each batter
        total_pas = baseline_df[['batter', 'clean_pa_count']].copy()
        total_pas.columns = ['batter', 'total_clean_pas']
        
        # Merge counts
        merged_df = merged_df.merge(bad_call_counts, on='batter', how='left')
        merged_df = merged_df.merge(total_pas, on='batter', how='left')
        
        # Estimate total PAs (clean + affected by bad calls)
        merged_df['estimated_total_pas'] = merged_df['total_clean_pas'] + merged_df['post_bad_call_count']
        
        # Calculate the proportion of PAs affected by bad calls
        merged_df['pct_pas_affected_by_bad_calls'] = (
            merged_df['post_bad_call_count'] / merged_df['estimated_total_pas'] * 100
        )
        
        # Estimate seasonal xwOBA improvement with robo-umps
        # This is the money metric for scouts
        merged_df['projected_xwoba_improvement'] = (
            merged_df['xwoba_decline_after_bad_calls'] * 
            merged_df['pct_pas_affected_by_bad_calls'] / 100
        )
        
        # Calculate current season estimate
        merged_df['current_season_xwoba_estimate'] = (
            merged_df['baseline_xwoba_mean'] * (merged_df['total_clean_pas'] / merged_df['estimated_total_pas']) +
            merged_df['post_bad_call_xwoba_mean'] * (merged_df['post_bad_call_count'] / merged_df['estimated_total_pas'])
        )
        
        merged_df['robo_ump_xwoba_estimate'] = (
            merged_df['current_season_xwoba_estimate'] + merged_df['projected_xwoba_improvement']
        )
        
        # Sort by projected improvement (highest impact players first)
        merged_df = merged_df.sort_values('projected_xwoba_improvement', ascending=False)
        
        # Filter for statistical significance and minimum sample size
        merged_df = merged_df[
            (merged_df['post_bad_call_count'] >= 20) & 
            (merged_df['total_clean_pas'] >= 50) &
            (merged_df['significance_score'] >= 1.0)  # Roughly p < 0.32, fairly liberal
        ].copy()
        
        return merged_df
    
    def generate_scouting_report(self, impact_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate actionable scouting insights"""
        
        if impact_df.empty:
            return {"error": "No data available for scouting report"}
        
        # Top undervalued targets (biggest xwOBA improvement potential)
        top_targets = impact_df.head(25).copy()
        
        # Categorize players by impact type
        high_impact = impact_df[impact_df['projected_xwoba_improvement'] >= 0.020]  # 20+ point improvement
        medium_impact = impact_df[
            (impact_df['projected_xwoba_improvement'] >= 0.010) & 
            (impact_df['projected_xwoba_improvement'] < 0.020)
        ]
        
        # Statistical summary
        summary_stats = {
            'total_players_analyzed': len(impact_df),
            'high_impact_players': len(high_impact),
            'medium_impact_players': len(medium_impact),
            'average_xwoba_improvement': float(impact_df['projected_xwoba_improvement'].mean()),
            'median_xwoba_improvement': float(impact_df['projected_xwoba_improvement'].median()),
            'max_xwoba_improvement': float(impact_df['projected_xwoba_improvement'].max()),
            'avg_pct_pas_affected': float(impact_df['pct_pas_affected_by_bad_calls'].mean())
        }
        
        return {
            'scouting_summary': summary_stats,
            'top_25_targets': top_targets.to_dict('records'),
            'high_impact_targets': high_impact[['batter', 'projected_xwoba_improvement', 
                                             'current_season_xwoba_estimate', 'robo_ump_xwoba_estimate',
                                             'pct_pas_affected_by_bad_calls']].to_dict('records'),
            'methodology_note': 'projected_xwoba_improvement represents estimated seasonal xwOBA increase with automated umpiring'
        }
    
    def run_full_analysis(self, processed_filename: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Run the complete psychological impact analysis"""
        
        # Load data
        df = self.load_processed_data(processed_filename)
        
        # Analyze incorrect calls and their context
        calls_df = self.analyze_post_call_performance(df)
        
        if calls_df.empty:
            self.logger.error("No bad calls data available")
            return pd.DataFrame(), {}
        
        # Calculate baseline performance (clean PAs only)
        baseline_df = self.calculate_baseline_performance(df)
        
        if baseline_df.empty:
            self.logger.error("No baseline data available")
            return pd.DataFrame(), {}
        
        # Analyze post-bad-call performance
        impact_analysis_df = self.analyze_performance_after_bad_calls(df, calls_df)
        
        if impact_analysis_df.empty:
            self.logger.error("No impact analysis data available")
            return pd.DataFrame(), {}
        
        # Calculate psychological impact scores
        final_analysis = self.calculate_psychological_impact_scores(baseline_df, impact_analysis_df)
        
        # Generate scouting report
        scouting_report = self.generate_scouting_report(final_analysis)
        
        # Save results
        output_path = self.reports_dir / "psychological_impact_analysis.json"
        with open(output_path, 'w') as f:
            json.dump(scouting_report, f, indent=2, default=str)
        
        csv_path = self.reports_dir / "undervalued_targets.csv"
        final_analysis.to_csv(csv_path, index=False)
        
        self.logger.info(f"Analysis complete! Results saved to {output_path} and {csv_path}")
        
        return final_analysis, scouting_report

if __name__ == "__main__":
    analyzer = UmpireImpactAnalyzer()
    
    # Example usage
    analysis_df, scouting_data = analyzer.run_full_analysis("statcast_2024_processed.csv")
    
    if not analysis_df.empty:
        print("Top 10 undervalued players (biggest xwOBA improvement with robo-umps):")
        top_10 = analysis_df.head(10)
        for _, player in top_10.iterrows():
            print(f"Player {player['batter']}: +{player['projected_xwoba_improvement']:.3f} xwOBA "
                  f"({player['current_season_xwoba_estimate']:.3f} → {player['robo_ump_xwoba_estimate']:.3f})")