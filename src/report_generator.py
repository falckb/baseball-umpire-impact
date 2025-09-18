"""
Interactive Scouting Report Generator
Creates HTML dashboard focused on identifying undervalued players
File location: src/report_generator.py
"""

import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from pathlib import Path
from typing import Dict, Any
import logging

class ScoutingReportGenerator:
    """Generate interactive scouting reports for undervalued player identification"""
    
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_analysis_data(self, csv_filename: str = "undervalued_targets.csv") -> pd.DataFrame:
        """Load the CSV analysis results"""
        filepath = self.reports_dir / csv_filename
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        return pd.read_csv(filepath)
    
    def load_scouting_report(self, json_filename: str = "psychological_impact_analysis.json") -> Dict[str, Any]:
        """Load the JSON scouting report data"""
        filepath = self.reports_dir / json_filename
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def create_xwoba_improvement_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create the money chart: xwOBA improvement potential"""
        top_25 = df.head(25).copy()
        
        # Create current vs potential xwOBA chart
        fig = go.Figure()
        
        # Current season estimate
        fig.add_trace(go.Bar(
            name='Current Season xwOBA',
            x=top_25['batter'].astype(str),
            y=top_25['current_season_xwoba_estimate'],
            marker_color='lightcoral',
            hovertemplate=
            '<b>Player:</b> %{x}<br>' +
            '<b>Current xwOBA:</b> %{y:.3f}<br>' +
            '<extra></extra>'
        ))
        
        # Robo-ump potential
        fig.add_trace(go.Bar(
            name='Robo-Ump Potential xwOBA',
            x=top_25['batter'].astype(str),
            y=top_25['robo_ump_xwoba_estimate'],
            marker_color='lightgreen',
            hovertemplate=
            '<b>Player:</b> %{x}<br>' +
            '<b>Robo-Ump xwOBA:</b> %{y:.3f}<br>' +
            '<extra></extra>'
        ))
        
        # Add improvement arrows/annotations for top 10
        for i, (_, player) in enumerate(top_25.head(10).iterrows()):
            improvement = player['projected_xwoba_improvement']
            fig.add_annotation(
                x=str(player['batter']),
                y=player['robo_ump_xwoba_estimate'] + 0.01,
                text=f"+{improvement:.3f}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="green",
                arrowwidth=2,
                font=dict(color="green", size=12, family="Arial Black")
            )
        
        fig.update_layout(
            title='Top 25 Undervalued Players: xwOBA Improvement Potential with Robo-Umps',
            xaxis_title='Player ID',
            yaxis_title='Expected wOBA (xwOBA)',
            barmode='group',
            height=600,
            showlegend=True,
            hovermode='x unified'
        )
        
        return fig
    
    def create_impact_distribution_chart(self, df: pd.DataFrame) -> go.Figure:
        """Show distribution of psychological impacts"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'xwOBA Improvement Distribution',
                'Percentage of PAs Affected',
                'Current vs Robo-Ump xwOBA',
                'Impact vs Sample Size'
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Distribution of improvements
        fig.add_trace(
            go.Histogram(
                x=df['projected_xwoba_improvement'], 
                nbinsx=20,
                name='Improvement',
                marker_color='lightblue'
            ),
            row=1, col=1
        )
        
        # Percentage of PAs affected
        fig.add_trace(
            go.Histogram(
                x=df['pct_pas_affected_by_bad_calls'], 
                nbinsx=20,
                name='% PAs Affected',
                marker_color='orange'
            ),
            row=1, col=2
        )
        
        # Current vs potential scatter
        fig.add_trace(
            go.Scatter(
                x=df['current_season_xwoba_estimate'],
                y=df['robo_ump_xwoba_estimate'],
                mode='markers',
                name='Current vs Potential',
                marker=dict(
                    size=df['projected_xwoba_improvement'] * 1000,  # Size by improvement
                    color=df['projected_xwoba_improvement'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Improvement")
                ),
                hovertemplate=
                '<b>Current xwOBA:</b> %{x:.3f}<br>' +
                '<b>Potential xwOBA:</b> %{y:.3f}<br>' +
                '<b>Improvement:</b> %{marker.color:.3f}<br>' +
                '<extra></extra>'
            ),
            row=2, col=1
        )
        
        # Add diagonal line for reference
        min_val = min(df['current_season_xwoba_estimate'].min(), df['robo_ump_xwoba_estimate'].min())
        max_val = max(df['current_season_xwoba_estimate'].max(), df['robo_ump_xwoba_estimate'].max())
        fig.add_trace(
            go.Scatter(
                x=[min_val, max_val], 
                y=[min_val, max_val],
                mode='lines',
                name='No Change Line',
                line=dict(dash='dash', color='red'),
                showlegend=False
            ),
            row=2, col=1
        )
        
        # Impact vs sample size
        fig.add_trace(
            go.Scatter(
                x=df['post_bad_call_count'],
                y=df['projected_xwoba_improvement'],
                mode='markers',
                name='Impact vs Sample',
                marker=dict(color='purple'),
                hovertemplate=
                '<b>Bad Call Sample:</b> %{x}<br>' +
                '<b>Improvement:</b> %{y:.3f}<br>' +
                '<extra></extra>'
            ),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=False)
        return fig
    
    def create_scouting_tiers_chart(self, df: pd.DataFrame) -> go.Figure:
        """Categorize players into scouting tiers"""
        
        # Define tiers
        df_copy = df.copy()
        df_copy['tier'] = 'Low Impact'
        df_copy.loc[df_copy['projected_xwoba_improvement'] >= 0.010, 'tier'] = 'Medium Impact'
        df_copy.loc[df_copy['projected_xwoba_improvement'] >= 0.020, 'tier'] = 'High Impact'
        df_copy.loc[df_copy['projected_xwoba_improvement'] >= 0.035, 'tier'] = 'Elite Target'
        
        # Color mapping
        color_map = {
            'Low Impact': 'lightgray',
            'Medium Impact': 'gold', 
            'High Impact': 'orange',
            'Elite Target': 'red'
        }
        
        fig = go.Figure()
        
        for tier in ['Elite Target', 'High Impact', 'Medium Impact', 'Low Impact']:
            tier_data = df_copy[df_copy['tier'] == tier]
            if len(tier_data) > 0:
                fig.add_trace(go.Scatter(
                    x=tier_data['current_season_xwoba_estimate'],
                    y=tier_data['projected_xwoba_improvement'],
                    mode='markers',
                    name=f'{tier} ({len(tier_data)})',
                    marker=dict(
                        color=color_map[tier],
                        size=10,
                        line=dict(width=1, color='black')
                    ),
                    hovertemplate=
                    '<b>Player:</b> %{customdata}<br>' +
                    '<b>Current xwOBA:</b> %{x:.3f}<br>' +
                    '<b>Improvement:</b> %{y:.3f}<br>' +
                    '<b>Tier:</b> ' + tier + '<br>' +
                    '<extra></extra>',
                    customdata=tier_data['batter']
                ))
        
        # Add threshold lines
        fig.add_hline(y=0.010, line_dash="dash", line_color="gray", 
                     annotation_text="Medium Impact Threshold")
        fig.add_hline(y=0.020, line_dash="dash", line_color="orange", 
                     annotation_text="High Impact Threshold") 
        fig.add_hline(y=0.035, line_dash="dash", line_color="red", 
                     annotation_text="Elite Target Threshold")
        
        fig.update_layout(
            title='Scouting Tiers: Player Value Hidden by Umpire Psychology',
            xaxis_title='Current Season xwOBA Estimate',
            yaxis_title='Projected xwOBA Improvement with Robo-Umps',
            height=600
        )
        
        return fig
    
    def generate_scouting_dashboard(self, 
                                  csv_filename: str = "undervalued_targets.csv",
                                  json_filename: str = "psychological_impact_analysis.json",
                                  output_filename: str = "scouting_dashboard.html") -> None:
        """Generate comprehensive scouting dashboard"""
        
        try:
            # Load data
            df = self.load_analysis_data(csv_filename)
            scouting_data = self.load_scouting_report(json_filename)
            
            if df.empty:
                self.logger.error("No data available for dashboard")
                return
                
        except FileNotFoundError as e:
            self.logger.error(f"Required data files not found: {e}")
            return
        
        # Create charts
        xwoba_chart = self.create_xwoba_improvement_chart(df)
        distribution_charts = self.create_impact_distribution_chart(df)
        scouting_tiers_chart = self.create_scouting_tiers_chart(df)
        
        # Get summary stats
        summary = scouting_data.get('scouting_summary', {})
        
        # Create comprehensive HTML dashboard
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Baseball Scouting: Undervalued Players Analysis</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                
                .dashboard-container {{
                    max-width: 1400px;
                    margin: 0 auto;
                }}
                
                .header {{ 
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    color: #333; 
                    padding: 30px; 
                    border-radius: 15px; 
                    margin-bottom: 30px; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
                
                .header h1 {{
                    margin: 0 0 10px 0;
                    font-size: 2.5em;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }}
                
                .subtitle {{
                    font-size: 1.2em;
                    color: #666;
                    margin: 0;
                }}
                
                .summary-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
                    gap: 20px; 
                    margin-bottom: 30px; 
                }}
                
                .summary-card {{ 
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    padding: 25px; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    transition: transform 0.3s ease;
                }}
                
                .summary-card:hover {{
                    transform: translateY(-5px);
                }}
                
                .stat-number {{ 
                    font-size: 2.5em; 
                    font-weight: bold; 
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin-bottom: 8px;
                }}
                
                .stat-label {{ 
                    font-size: 0.95em; 
                    color: #666; 
                    font-weight: 500;
                }}
                
                .chart-container {{ 
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    padding: 25px; 
                    border-radius: 15px; 
                    margin-bottom: 30px; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
                
                .insight-box {{
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 15px;
                    margin: 30px 0;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                }}
                
                .insight-box h3 {{
                    margin: 0 0 15px 0;
                    font-size: 1.4em;
                }}
                
                .top-targets {{
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    padding: 25px;
                    border-radius: 15px;
                    margin-bottom: 30px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
                
                .target-list {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 15px;
                    margin-top: 20px;
                }}
                
                .target-item {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    border-left: 4px solid #667eea;
                }}
                
                .target-player {{
                    font-weight: bold;
                    font-size: 1.1em;
                    color: #333;
                }}
                
                .target-improvement {{
                    color: #28a745;
                    font-weight: bold;
                    font-size: 1.2em;
                }}
                
                .methodology {{ 
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    padding: 25px; 
                    border-radius: 15px; 
                    border-left: 4px solid #667eea;
                    margin-top: 30px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                }}
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <div class="header">
                    <h1>🎯 Baseball Scouting: Undervalued Players</h1>
                    <p class="subtitle">Identifying players whose true talent is masked by psychological reactions to bad umpire calls</p>
                </div>
                
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="stat-number">{summary.get('total_players_analyzed', 0)}</div>
                        <div class="stat-label">Players Analyzed</div>
                    </div>
                    <div class="summary-card">
                        <div class="stat-number">{summary.get('high_impact_players', 0)}</div>
                        <div class="stat-label">High Impact Targets</div>
                    </div>
                    <div class="summary-card">
                        <div class="stat-number">+{summary.get('average_xwoba_improvement', 0):.3f}</div>
                        <div class="stat-label">Avg xwOBA Improvement</div>
                    </div>
                    <div class="summary-card">
                        <div class="stat-number">+{summary.get('max_xwoba_improvement', 0):.3f}</div>
                        <div class="stat-label">Max xwOBA Improvement</div>
                    </div>
                </div>
                
                <div class="insight-box">
                    <h3>💡 Key Scouting Insight</h3>
                    <p>Players showing <strong>+0.020 xwOBA improvement</strong> potential represent significant undervalued targets. 
                    These players' current performance is being suppressed by psychological reactions to incorrect umpire calls. 
                    With automated umpiring on the horizon, these players could see substantial performance improvements.</p>
                </div>
                
                <div class="chart-container">
                    <div id="xwoba-chart"></div>
                </div>
                
                <div class="chart-container">
                    <div id="tiers-chart"></div>
                </div>
                
                <div class="chart-container">
                    <div id="distribution-charts"></div>
                </div>
                
                <div class="top-targets">
                    <h3>🎯 Top 10 Undervalued Targets</h3>
                    <div class="target-list">"""
        
        # Add top 10 targets
        for i, target in enumerate(scouting_data.get('top_25_targets', [])[:10]):
            improvement = target.get('projected_xwoba_improvement', 0)
            current = target.get('current_season_xwoba_estimate', 0)
            potential = target.get('robo_ump_xwoba_estimate', 0)
            
            html_template += f"""
                        <div class="target-item">
                            <div class="target-player">Player {target.get('batter', 'Unknown')}</div>
                            <div class="target-improvement">+{improvement:.3f} xwOBA improvement</div>
                            <div style="font-size: 0.9em; color: #666; margin-top: 5px;">
                                {current:.3f} → {potential:.3f} xwOBA
                            </div>
                        </div>"""
        
        html_template += f"""
                    </div>
                </div>
                
                <div class="methodology">
                    <h3>📊 Methodology</h3>
                    <ul>
                        <li><strong>Psychological Impact Analysis:</strong> Compares performance in clean plate appearances vs. plate appearances following incorrect calls</li>
                        <li><strong>xwOBA Improvement:</strong> Estimates seasonal xwOBA increase if player performed at baseline level instead of suppressed post-bad-call level</li>
                        <li><strong>Statistical Significance:</strong> Requires minimum 50 clean PAs, 20 post-bad-call PAs, and significance score ≥ 1.0</li>
                        <li><strong>Scouting Value:</strong> Players with +0.020+ xwOBA improvement represent significant undervalued targets</li>
                    </ul>
                </div>
            </div>
            
            <script>
                // Render charts
                var xwobaData = {xwoba_chart.to_dict()['data']};
                var xwobaLayout = {xwoba_chart.to_dict()['layout']};
                Plotly.newPlot('xwoba-chart', xwobaData, xwobaLayout);
                
                var tiersData = {scouting_tiers_chart.to_dict()['data']};
                var tiersLayout = {scouting_tiers_chart.to_dict()['layout']};
                Plotly.newPlot('tiers-chart', tiersData, tiersLayout);
                
                var distData = {distribution_charts.to_dict()['data']};
                var distLayout = {distribution_charts.to_dict()['layout']};
                Plotly.newPlot('distribution-charts', distData, distLayout);
            </script>
        </body>
        </html>
        """
        
        # Save dashboard
        output_path = self.reports_dir / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        self.logger.info(f"Scouting dashboard saved to {output_path}")
        
        # Save individual charts for reference
        xwoba_chart.write_html(self.reports_dir / "xwoba_improvement_chart.html")
        scouting_tiers_chart.write_html(self.reports_dir / "scouting_tiers_chart.html")
        distribution_charts.write_html(self.reports_dir / "distribution_charts.html")

if __name__ == "__main__":
    generator = ScoutingReportGenerator()
    generator.generate_scouting_dashboard()
    print("Scouting dashboard generated!")