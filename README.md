# Baseball Umpire Impact Analysis

This project analyzes baseball pitch-by-pitch data to identify which players would benefit most from automated ball/strike calling (robo-umps). By examining incorrect umpire calls and their context, we can quantify the impact of human umpiring errors on individual batters.

## Overview

The analysis examines:
- Incorrect ball/strike calls for each qualified batter (300+ PA)
- Count situations where incorrect calls occurred  
- Leverage/importance of each incorrect call
- Net impact of incorrect calls (calls against vs. calls for each batter)
- Potential benefit each player would receive from perfect umpiring

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
│   ├── data_collector.py    # Baseball Savant API interface
│   ├── data_processor.py    # Data cleaning and structuring  
│   ├── umpire_analyzer.py   # Core analysis engine
│   ├── report_generator.py  # Interactive dashboard creation
│   └── main_pipeline.py     # Complete workflow orchestration
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

### Strike Zone Definition
- **Horizontal:** ±0.83 feet from home plate center
- **Vertical:** Dynamic based on each batter's `sz_top` and `sz_bot` values from Statcast

### Leverage Scoring
Each count situation is assigned a leverage weight based on its impact on the at-bat outcome:

| Count | Leverage | Description |
|-------|----------|-------------|
| 3-2   | 1.6      | Full count - highest leverage |
| 3-0   | 1.5      | Walk very likely |
| 3-1   | 1.4      | Very batter-friendly |
| 2-0   | 1.3      | Batter-friendly |
| 2-1   | 1.2      | Slight batter advantage |
| 2-2   | 1.1      | Full count approaching |
| 0-0, 1-1 | 1.0   | Neutral |
| 1-0   | 1.1      | Slight batter advantage |
| 0-1   | 0.9      | Slight pitcher advantage |
| 1-2   | 0.8      | Pitcher advantage |
| 0-2   | 0.7      | Strong pitcher advantage |

### Benefit Score Calculation
**Potential Benefit Score** = (Weighted incorrect calls against batter - Weighted incorrect calls for batter) / Total PA × 100

This represents the weighted impact of incorrect calls per 100 plate appearances.

## Output Files

After running the analysis, you'll find:

1. **`reports/umpire_impact_dashboard.html`** - Interactive web dashboard with visualizations
2. **`reports/top_beneficiaries.csv`** - Top 50 players who would benefit most  
3. **`reports/umpire_impact_report.json`** - Complete analysis results in JSON format
4. **`data/processed/statcast_YYYY_processed.csv`** - Cleaned plate appearance data
5. **`data/raw/statcast_YYYY_raw.csv`** - Raw pitch-by-pitch data

## Key Metrics Explained

### Player-Level Metrics
- **Potential Benefit Score:** Primary ranking metric - weighted incorrect calls against per 100 PA
- **Net Calls Against:** Raw count of incorrect calls hurting vs. helping the batter
- **High Leverage Calls Against:** Incorrect calls in high-impact situations (leverage ≥ 1.3)
- **Incorrect Calls per PA:** Overall rate of incorrect calls experienced

### Situational Analysis
- **Count Analysis:** Breakdown of incorrect calls by ball-strike count
- **Leverage Distribution:** How incorrect calls distribute across game situations
- **Impact Patterns:** Which types of calls are most commonly missed

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

After running the analysis, you might see results like:

```
Top 5 players who would benefit most from automated umpiring:
  Player 12345: 2.34 benefit score (8 net calls against, 3 high-leverage)
  Player 67890: 2.12 benefit score (6 net calls against, 4 high-leverage)
  Player 11111: 1.98 benefit score (7 net calls against, 2 high-leverage)
  ...
```

Open `reports/umpire_impact_dashboard.html` in your browser to explore the full interactive analysis!