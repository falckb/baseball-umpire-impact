"""
Main Pipeline for Baseball Umpire Impact Analysis
Orchestrates the complete workflow from data collection to reporting
"""

import argparse
import logging
from pathlib import Path
import sys
from datetime import datetime

# Import our custom modules
from data_collector import BaseballSavantCollector
from data_processor import StatcastProcessor
from umpire_analyzer import UmpireImpactAnalyzer
from report_generator import ScoutingReportGenerator

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('umpire_analysis.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def run_full_pipeline(year: int = 2024, min_pa: int = 300, 
                     chunk_days: int = 14, force_redownload: bool = False):
    """
    Run the complete analysis pipeline
    
    Args:
        year: Season year to analyze
        min_pa: Minimum plate appearances for qualification
        chunk_days: Days per API call (to manage rate limits)
        force_redownload: Whether to redownload data if it exists
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting umpire impact analysis for {year} season")
    
    # Create directory structure
    directories = ['data/raw', 'data/processed', 'reports', 'config']
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # File paths
    raw_filename = f"statcast_{year}_raw.csv"
    processed_filename = f"statcast_{year}_processed.csv"
    
    # Step 1: Data Collection
    logger.info("=== STEP 1: DATA COLLECTION ===")
    collector = BaseballSavantCollector()
    
    raw_file_path = Path(f"data/raw/{raw_filename}")
    if not raw_file_path.exists() or force_redownload:
        logger.info(f"Downloading Statcast data for {year}...")
        raw_df = collector.collect_season_data(year, chunk_days=chunk_days)
        
        if raw_df.empty:
            logger.error("No data collected! Check your internet connection and API access.")
            return False
            
        logger.info(f"Successfully collected {len(raw_df)} pitch records")
    else:
        logger.info(f"Raw data file {raw_filename} already exists. Use --force-redownload to refresh.")
    
    # Step 2: Data Processing
    logger.info("=== STEP 2: DATA PROCESSING ===")
    processor = StatcastProcessor()
    
    processed_file_path = Path(f"data/processed/{processed_filename}")
    if not processed_file_path.exists() or force_redownload:
        logger.info("Processing raw Statcast data...")
        processed_df = processor.process_full_dataset(raw_filename, processed_filename)
        
        if processed_df.empty:
            logger.error("No data after processing! Check data quality and filters.")
            return False
            
        logger.info(f"Successfully processed {len(processed_df)} plate appearances")
    else:
        logger.info(f"Processed data file {processed_filename} already exists. Use --force-redownload to refresh.")
    
    # Step 3: Psychological Impact Analysis
    logger.info("=== STEP 3: PSYCHOLOGICAL IMPACT ANALYSIS ===")
    analyzer = UmpireImpactAnalyzer()
    
    logger.info("Analyzing psychological impact of bad calls on player performance...")
    analysis_df, scouting_report = analyzer.run_full_analysis(processed_filename)
    
    if analysis_df.empty:
        logger.error("No psychological impact data generated! Check data quality.")
        return False
    
    # Print scouting summary
    logger.info(f"Analysis complete! Found {len(analysis_df)} players with significant psychological impact.")
    
    if not analysis_df.empty:
        logger.info("Top 5 undervalued targets (biggest xwOBA improvement potential):")
        top_5 = analysis_df.head(5)
        for _, player in top_5.iterrows():
            current = player['current_season_xwoba_estimate']
            potential = player['robo_ump_xwoba_estimate'] 
            improvement = player['projected_xwoba_improvement']
            logger.info(f"  Player {player['batter']}: +{improvement:.3f} xwOBA ({current:.3f} → {potential:.3f})")
    
    # Step 4: Scouting Report Generation
    logger.info("=== STEP 4: SCOUTING REPORT GENERATION ===")
    report_generator = ScoutingReportGenerator()
    
    logger.info("Generating interactive scouting dashboard...")
    report_generator.generate_scouting_dashboard()
    
    logger.info("=== SCOUTING ANALYSIS COMPLETE ===")
    logger.info("Files generated:")
    logger.info(f"  - Raw data: data/raw/{raw_filename}")
    logger.info(f"  - Processed data: data/processed/{processed_filename}")
    logger.info(f"  - Undervalued targets: reports/undervalued_targets.csv")
    logger.info(f"  - Psychological analysis: reports/psychological_impact_analysis.json")
    logger.info(f"  - Scouting dashboard: reports/scouting_dashboard.html")
    logger.info("")
    logger.info("🎯 SCOUTING INSIGHT: Open reports/scouting_dashboard.html to identify undervalued players!")
    
    return True

def run_analysis_only(year: int = 2024):
    """
    Run only the analysis and reporting steps (assuming data already exists)
    """
    logger = logging.getLogger(__name__)
    processed_filename = f"statcast_{year}_processed.csv"
    
    # Check if processed data exists
    if not Path(f"data/processed/{processed_filename}").exists():
        logger.error(f"Processed data file {processed_filename} not found!")
        logger.error("Run with --full-pipeline first to collect and process data.")
        return False
    
    # Step 3: Analysis
    logger.info("=== RUNNING PSYCHOLOGICAL IMPACT ANALYSIS ===")
    analyzer = UmpireImpactAnalyzer()
    analysis_df, scouting_report = analyzer.run_full_analysis(processed_filename)
    
    # Step 4: Report Generation
    report_generator = ScoutingReportGenerator()
    report_generator.generate_scouting_dashboard()
    
    logger.info("Scouting analysis and reporting complete!")
    logger.info("🎯 Open reports/scouting_dashboard.html to identify undervalued players!")
    return True

def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Baseball Umpire Impact Analysis')
    
    parser.add_argument('--year', type=int, default=2024, 
                       help='Season year to analyze (default: 2024)')
    parser.add_argument('--min-pa', type=int, default=300,
                       help='Minimum plate appearances for qualification (default: 300)')
    parser.add_argument('--chunk-days', type=int, default=14,
                       help='Days per API call for rate limiting (default: 14)')
    parser.add_argument('--full-pipeline', action='store_true',
                       help='Run complete pipeline from data collection to reporting')
    parser.add_argument('--analysis-only', action='store_true',
                       help='Run only analysis and reporting (requires existing processed data)')
    parser.add_argument('--force-redownload', action='store_true',
                       help='Force redownload of data even if files exist')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Validate arguments
    if not args.full_pipeline and not args.analysis_only:
        logger.error("Must specify either --full-pipeline or --analysis-only")
        parser.print_help()
        return
    
    success = False  # Initialize success variable
    
    try:
        if args.full_pipeline:
            success = run_full_pipeline(
                year=args.year,
                min_pa=args.min_pa,
                chunk_days=args.chunk_days,
                force_redownload=args.force_redownload
            )
        elif args.analysis_only:
            success = run_analysis_only(year=args.year)
        
        if success:
            logger.info("🎉 Scouting analysis completed successfully!")
            logger.info("🎯 Open reports/scouting_dashboard.html in your browser to identify undervalued players.")
        else:
            logger.error("❌ Analysis failed. Check logs for details.")
            
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()