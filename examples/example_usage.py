"""
Example Usage Script
Shows how to use the scouting analysis for different scenarios
File location: examples/example_usage.py (create examples/ directory)
"""

import sys
import os
sys.path.append('src')

from data_collector import BaseballSavantCollector
from data_processor import StatcastProcessor
from umpire_analyzer import UmpireImpactAnalyzer
from report_generator import ScoutingReportGenerator
import pandas as pd

def example_quick_analysis():
    """Example: Quick analysis for recent data"""
    print("=== QUICK SCOUTING ANALYSIS EXAMPLE ===")
    
    # Collect just a few days of data for testing
    collector = BaseballSavantCollector()
    
    # Get recent data (adjust dates as needed)
    df = collector.get_statcast_data('2024-06-01', '2024-06-07')
    
    if df.empty:
        print("No data retrieved. Check your date range and internet connection.")
        return
    
    print(f"Retrieved {len(df)} pitch records")
    
    # Process the data
    processor = StatcastProcessor()
    
    # Save raw data temporarily
    raw_path = 'data/raw/example_data.csv'
    df.to_csv(raw_path, index=False)
    
    # Process it
    processed_df = processor.process_full_dataset('example_data.csv', 'example_processed.csv')
    
    if processed_df.empty:
        print("No processed data. Try a larger date range.")
        return
    
    print(f"Processed into {len(processed_df)} plate appearances")
    
    # Run psychological impact analysis
    analyzer = UmpireImpactAnalyzer()
    analysis_df, scouting_report = analyzer.run_full_analysis('example_processed.csv')
    
    if analysis_df.empty:
        print("No psychological impact found. Need more data with sufficient bad calls.")
        return
    
    # Show top results
    print("\nTop undervalued targets from this sample:")
    for _, player in analysis_df.head(5).iterrows():
        improvement = player['projected_xwoba_improvement']
        current = player['current_season_xwoba_estimate']
        potential = player['robo_ump_xwoba_estimate']
        print(f"Player {player['batter']}: +{improvement:.3f} xwOBA ({current:.3f} → {potential:.3f})")

def example_player_lookup():
    """Example: Look up specific player's psychological impact"""
    print("\n=== PLAYER LOOKUP EXAMPLE ===")
    
    # Load existing analysis results
    try:
        df = pd.read_csv('reports/undervalued_targets.csv')
    except FileNotFoundError:
        print("No analysis results found. Run the main pipeline first.")
        return
    
    # Get top player
    if df.empty:
        print("No data in analysis results.")
        return
        
    top_player = df.iloc[0]
    
    print(f"Most undervalued player analysis:")
    print(f"Player ID: {top_player['batter']}")
    print(f"Current season xwOBA estimate: {top_player['current_season_xwoba_estimate']:.3f}")
    print(f"Robo-ump xwOBA potential: {top_player['robo_ump_xwoba_estimate']:.3f}")
    print(f"Projected improvement: +{top_player['projected_xwoba_improvement']:.3f}")
    print(f"Percentage of PAs affected by bad calls: {top_player['pct_pas_affected_by_bad_calls']:.1f}%")
    
    # Scouting recommendation
    improvement = top_player['projected_xwoba_improvement']
    if improvement >= 0.035:
        tier = "ELITE TARGET 🎯"
    elif improvement >= 0.020:
        tier = "HIGH IMPACT TARGET 📈"
    elif improvement >= 0.010:
        tier = "MEDIUM IMPACT TARGET 📊"
    else:
        tier = "LOW IMPACT TARGET 📉"
    
    print(f"Scouting tier: {tier}")

def example_team_analysis():
    """Example: Analyze all players from a specific team perspective"""
    print("\n=== TEAM ANALYSIS EXAMPLE ===")
    
    try:
        df = pd.read_csv('reports/undervalued_targets.csv')
    except FileNotFoundError:
        print("No analysis results found. Run the main pipeline first.")
        return
    
    if df.empty:
        print("No data in analysis results.")
        return
    
    # Categorize players by impact level
    elite = df[df['projected_xwoba_improvement'] >= 0.035]
    high = df[(df['projected_xwoba_improvement'] >= 0.020) & (df['projected_xwoba_improvement'] < 0.035)]
    medium = df[(df['projected_xwoba_improvement'] >= 0.010) & (df['projected_xwoba_improvement'] < 0.020)]
    
    print("SCOUTING SUMMARY BY TIER:")
    print(f"Elite targets (≥0.035 xwOBA improvement): {len(elite)} players")
    print(f"High impact targets (0.020-0.035): {len(high)} players") 
    print(f"Medium impact targets (0.010-0.020): {len(medium)} players")
    
    print(f"\nTotal undervalued players identified: {len(df)}")
    print(f"Average xwOBA improvement potential: +{df['projected_xwoba_improvement'].mean():.3f}")
    print(f"Best single target improvement: +{df['projected_xwoba_improvement'].max():.3f}")

def example_free_agent_analysis():
    """Example: Focus on high-impact free agent targets"""
    print("\n=== FREE AGENT TARGET ANALYSIS ===")
    
    try:
        df = pd.read_csv('reports/undervalued_targets.csv')
    except FileNotFoundError:
        print("No analysis results found. Run the main pipeline first.")
        return
    
    # Focus on players with significant improvement potential
    # These are likely to be undervalued in the market
    targets = df[df['projected_xwoba_improvement'] >= 0.020].copy()
    
    if targets.empty:
        print("No high-impact targets found in current analysis.")
        return
    
    print("HIGH-VALUE FREE AGENT TARGETS:")
    print("(Players whose market value likely doesn't reflect robo-ump potential)\n")
    
    for i, (_, player) in enumerate(targets.head(10).iterrows(), 1):
        improvement = player['projected_xwoba_improvement']
        current = player['current_season_xwoba_estimate']
        potential = player['robo_ump_xwoba_estimate']
        affected_pct = player['pct_pas_affected_by_bad_calls']
        
        print(f"{i:2d}. Player {player['batter']}")
        print(f"    Market perception (current): {current:.3f} xwOBA")
        print(f"    True talent (robo-ump):      {potential:.3f} xwOBA")
        print(f"    Hidden value:                +{improvement:.3f} ({improvement*1000:.0f} points)")
        print(f"    PAs affected by psychology:  {affected_pct:.1f}%")
        print()

def main():
    """Run all examples"""
    print("🎯 BASEBALL SCOUTING ANALYSIS EXAMPLES")
    print("=" * 50)
    
    # Check if we have existing results
    import os
    if os.path.exists('reports/undervalued_targets.csv'):
        print("Found existing analysis results. Running examples...")
        example_player_lookup()
        example_team_analysis() 
        example_free_agent_analysis()
    else:
        print("No existing analysis found. Running quick sample analysis...")
        print("(For full analysis, run: python src/main_pipeline.py --full-pipeline)")
        example_quick_analysis()
    
    print("\n" + "=" * 50)
    print("💡 TIP: Run 'python src/main_pipeline.py --full-pipeline --year 2024' for complete analysis")
    print("💡 TIP: Open reports/scouting_dashboard.html for interactive exploration")

if __name__ == "__main__":
    main()