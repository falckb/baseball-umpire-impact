# Baseball Scouting: Undervalued Players Analysis

This project identifies baseball players whose true talent is masked by their psychological reactions to incorrect umpire calls. By analyzing how players perform after experiencing bad calls, we can identify undervalued targets who would significantly improve with automated umpiring.

## 🎯 Scouting Application

**The Goal:** Find players whose season xwOBA would be significantly higher (e.g., +0.045 points) if they didn't experience the psychological impact of incorrect umpire calls.

**Why This Matters for Scouts:**
- Identify undervalued free agents and trade targets
- Players negatively affected by bad calls may be available below their true talent level
- With automated umpiring expanding, these players represent excellent value opportunities
- Provides objective data on which players struggle psychologically with umpire inconsistency

## Overview

The analysis examines:
- **Baseline Performance:** How each batter performs in "clean" plate appearances (no incorrect calls against them)
- **Post-Bad-Call Performance:** How the same batter performs in subsequent plate appearances after experiencing incorrect calls
- **Psychological Impact:** The measurable difference in performance after bad call experiences
- **xwOBA Projection:** Estimated seasonal improvement if player maintained baseline performance level

## Key Insights

Instead of leverage-weighted call analysis, this focuses on:
1. **Emotional/Psychological Impact:** Some players get rattled by bad calls, others don't
2. **Performance Suppression:** Quantifying how much bad calls hurt subsequent performance
3. **Seasonal Projections:** "Player X's xwOBA would likely be ~0.045 points higher with robo-umps"
4. **Scouting Value:** Identifying players whose market value doesn't reflect their robo-ump potential

## Project Structure

```
baseball-umpire-impact/
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   └── config.yaml          # Configuration settings
├── src/
│   ├── __init__.py
│   ├── main_pipeline.py     # Complete workflow orchestration
│   ├── data_collector.py    # Baseball Savant API interface
│   ├── data_processor.py    # Data cleaning and structuring  
│   ├── umpire_analyzer.py   # Psychological impact analysis engine
│   └── report_generator.py  # Interactive scouting dashboard creation
├── data/
│   ├── raw/                 # Raw Statcast data
│   └── processed/           # Cleaned and structured data
├── reports/                 # Analysis outputs and dashboard
├── notebooks/               # Jupyter notebooks for exploration
└── tests/                   # Unit tests (future)
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/baseball-umpire-impact.git
   cd baseball-umpire-impact
   ```

2. **Set up virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux  
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start - Full Pipeline

Run the complete analysis for the 2024 season:

```bash
python src/main_pipeline.py --full-pipeline --year 2024
```

### Analysis Only (if you already have processed data)

```bash
python src/main_pipeline.py --analysis-only --year 2024
```

### Command Line Options

- `--year YYYY`: Season year to analyze (default: 2024)
- `--min-pa N`: Minimum plate appearances for qualification (default: 300)  
- `--chunk-days N`: Days per API call for rate limiting (default: 14)
- `--full-pipeline`: Run complete pipeline from data collection to reporting
- `--analysis-only`: Run only analysis and reporting (requires existing processed data)
- `--force-redownload`: Force redownload of data even if files exist

### Individual Module Usage

#### Data Collection
```python
from src.data_collector import BaseballSavantCollector

collector = BaseballSavantCollector()
df = collector.collect_season_data(2024)
```

#### Data Processing  
```python
from src.data_processor import StatcastProcessor

processor = StatcastProcessor()
processed_df = processor.process_full_dataset("statcast_2024_raw.csv")
```

#### Analysis
```python
from src.umpire_analyzer import UmpireImpactAnalyzer

analyzer = UmpireImpactAnalyzer()
analysis_df, situations = analyzer.run_full_analysis("statcast_2024_processed.csv")
```

#### Report Generation
```python
from src.report_generator import InteractiveReportGenerator

generator = InteractiveReportGenerator()
generator.generate_html_report()
```

## Methodology

### Psychological Impact Analysis

1. **Baseline Performance Calculation:**
   - Identifies "clean" plate appearances with no incorrect calls against the batter
   - Calculates baseline wOBA and xwOBA for each qualified player (50+ clean PAs)

2. **Post-Bad-Call Performance:**
   - Tracks performance in plate appearances following incorrect calls against the batter
   - Analyzes next 10 PAs after each bad call experience
   - Measures performance degradation due to psychological impact

3. **Statistical Significance:**
   - Requires minimum sample sizes (50 clean PAs, 20 post-bad-call PAs)
   - Uses significance testing to identify meaningful performance differences
   - Filters out random variation to focus on genuine psychological impact

4. **Seasonal Projection:**
   - **Key Formula:** `Projected xwOBA Improvement = (Baseline Performance - Post-Bad-Call Performance) × Percentage of PAs Affected`
   - Estimates what player's season xwOBA would be without psychological suppression
   - Provides actionable scouting metric: "Player X would gain +0.045 xwOBA with robo-umps"

### Scouting Tiers
- **Elite Targets:** +0.035+ xwOBA improvement potential
- **High Impact:** +0.020 to +0.035 xwOBA improvement
- **Medium Impact:** +0.010 to +0.020 xwOBA improvement  
- **Low Impact:** <+0.010 xwOBA improvement

## Output Files

After running the analysis, you'll find:

1. **`reports/scouting_dashboard.html`** - Interactive scouting dashboard with player valuations
2. **`reports/undervalued_targets.csv`** - Complete analysis of all qualified players
3. **`reports/psychological_impact_analysis.json`** - Detailed scouting report with tiers
4. **`data/processed/statcast_YYYY_processed.csv`** - Cleaned plate appearance data
5. **`data/raw/statcast_YYYY_raw.csv`** - Raw pitch-by-pitch data

## Key Scouting Metrics

### Player-Level Metrics
- **Projected xwOBA Improvement:** Primary scouting metric - estimated seasonal xwOBA gain with robo-umps
- **Current vs Robo-Ump xwOBA:** Direct comparison showing hidden value (e.g., .342 → .387)
- **Psychological Impact Score:** How much performance drops after bad calls
- **Percentage of PAs Affected:** What portion of season was impacted by bad call psychology

### Market Application
- **Undervalued Free Agents:** Players with high improvement potential trading below true talent
- **Trade Targets:** Teams can acquire players whose struggles are umpire-related, not skill-related  
- **Contract Negotiations:** Objective data on which players are systematically underperforming
- **Future Planning:** With robo-umps expanding, these players represent excellent value

## Data Sources

- **Baseball Savant/Statcast:** Pitch-by-pitch data including location, count, and outcome
- **Strike Zone:** MLB official strike zone boundaries with batter-specific height adjustments

## Limitations

1. **Strike Zone Approximation:** Uses standard boundaries; actual umpire zones may vary
2. **Sample Size:** Requires 300+ PA, limiting analysis to regular players
3. **Context:** Doesn't account for game situation, score, or strategic factors
4. **API Limits:** Data collection may take time due to rate limiting

## Future Enhancements

- [ ] Pitcher impact analysis (which pitchers are hurt most by bad calls)
- [ ] Team-level analysis and rankings  
- [ ] Historical trend analysis across multiple seasons
- [ ] Game situation context (inning, score, runners on base)
- [ ] Umpire-specific analysis and consistency metrics
- [ ] Machine learning models to predict call accuracy

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Baseball Savant/MLB:** For providing comprehensive Statcast data
- **Plotly:** For interactive visualization capabilities
- **Baseball analytics community:** For methodology inspiration and validation

## Contact

For questions, suggestions, or collaboration opportunities, please open an issue on GitHub.

---

## Quick Example Results

After running the analysis, you might see scouting results like:

```
Top 5 undervalued targets (biggest xwOBA improvement potential):
  Player 12345: +0.047 xwOBA (0.342 → 0.389) - Elite Target
  Player 67890: +0.033 xwOBA (0.315 → 0.348) - High Impact  
  Player 11111: +0.028 xwOBA (0.298 → 0.326) - High Impact
  Player 22222: +0.021 xwOBA (0.331 → 0.352) - High Impact
  Player 33333: +0.018 xwOBA (0.307 → 0.325) - Medium Impact
```

**Scouting Translation:** Player 12345 is significantly undervalued - their season performance is suppressed by ~47 points of xwOBA due to psychological reactions to bad umpire calls. With automated umpiring expanding, this player represents excellent value.

Open `reports/scouting_dashboard.html` in your browser to explore the full interactive scouting analysis!

## File Locations Summary

Here's exactly where each code file belongs in your project structure:

### Root Directory Files
- `README.md` - Project documentation (you're reading it!)
- `requirements.txt` - Python package dependencies
- `.gitignore` - Git ignore patterns
- `setup.py` - Project setup and installation script
- `test_installation.py` - Installation verification script

### Configuration Files (`config/` directory)
- `config/config.yaml` - Main configuration settings
- `config/local_config_template.yaml` - Template for local overrides

### Python Source Code (`src/` directory)
- `src/__init__.py` - Makes src a Python package
- `src/main_pipeline.py` - **Main script to run everything**
- `src/data_collector.py` - Baseball Savant API data collection
- `src/data_processor.py` - Data cleaning and structuring
- `src/umpire_analyzer.py` - **Core psychological impact analysis**
- `src/report_generator.py` - Interactive dashboard generation

### Data Files (created automatically)
- `data/raw/statcast_YYYY_raw.csv` - Raw API data
- `data/processed/statcast_YYYY_processed.csv` - Cleaned data

### Output Files (created automatically)  
- `reports/scouting_dashboard.html` - **Main scouting dashboard**
- `reports/undervalued_targets.csv` - All player analysis results
- `reports/psychological_impact_analysis.json` - Detailed scouting report

### Empty Directories (created by setup)
- `notebooks/` - For Jupyter notebook exploration
- `tests/` - For unit tests (future)
- `logs/` - Log files

## Implementation Steps

1. **Set up your GitHub repository and clone it locally**

2. **Copy all the code files to their correct locations:**
   ```bash
   # After cloning your repo, create this exact structure:
   your-repo/
   ├── src/main_pipeline.py          # ← The orchestration script
   ├── src/data_collector.py         # ← API interface
   ├── src/data_processor.py         # ← Data cleaning
   ├── src/umpire_analyzer.py        # ← Psychological analysis (MODIFIED)
   ├── src/report_generator.py       # ← Scouting dashboard (MODIFIED)
   ├── config/config.yaml            # ← Settings
   ├── requirements.txt              # ← Dependencies
   ├── setup.py                      # ← Installation script
   └── README.md                     # ← This documentation
   ```

3. **Run the setup script:**
   ```bash
   python setup.py
   ```

4. **Test your installation:**
   ```bash
   python test_installation.py
   ```

5. **Run the full scouting analysis:**
   ```bash
   python src/main_pipeline.py --full-pipeline --year 2024
   ```

6. **View your scouting results:**
   ```bash
   # Open this file in your browser:
   reports/scouting_dashboard.html
   ```

The key difference from our original design is that we've refocused the analysis engine (`umpire_analyzer.py`) and dashboard (`report_generator.py`) on **psychological impact and scouting value** rather than leverage-weighted umpire accuracy.2.34 benefit score (8 net calls against, 3 high-leverage)
  Player 67890: 2.12 benefit score (6 net calls against, 4 high-leverage)
  Player 11111: 1.98 benefit score (7 net calls against, 2 high-leverage)
  ...
```

Open `reports/umpire_impact_dashboard.html` in your browser to explore the full interactive analysis!