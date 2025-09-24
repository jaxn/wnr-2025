#!/usr/bin/env python3
"""
Generate final results table for WNR 2025 series.
Creates a final_results.md file with a table where each row is a boat 
and each column is a week's race.
"""

import json
import pandas as pd
from typing import Dict, List, Optional

def load_results_data(filename: str = 'results.json') -> Dict:
    """Load the series results from JSON file."""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_results_table(data: Dict) -> pd.DataFrame:
    """Create a DataFrame with boats as rows and race weeks as columns."""
    
    # Get all boats and weeks
    all_boats = sorted(data['series']['boats_seen'])
    weeks = data['series']['weeks']
    
    # Create a DataFrame with boats as index and race dates as columns
    race_dates = [week['date'] for week in weeks]
    df = pd.DataFrame(index=all_boats, columns=race_dates)
    
    # Fill in the scores for each boat in each race
    for week in weeks:
        date = week['date']
        
        # Use 'results' key if available, otherwise 'results_provisional'
        results_key = 'results' if 'results' in week else 'results_provisional'
        if results_key not in week:
            continue
            
        for result in week[results_key]:
            boat = result['boat']
            score = result.get('score', '')
            
            # Handle DNC (Did Not Compete) specially
            if result.get('status') == 'DNC':
                df.loc[boat, date] = f"DNC({score})"
            elif result.get('status') == 'DSQ':
                df.loc[boat, date] = f"DSQ({score})"
            elif result.get('status') == 'DNF':
                df.loc[boat, date] = f"DNF({score})"
            else:
                # Show position if available, otherwise just score
                pos = result.get('pos')
                if pos is not None:
                    df.loc[boat, date] = f"{pos}({score})"
                else:
                    df.loc[boat, date] = str(score) if score != '' else '-'
    
    # Fill NaN values with '-' for races where boat didn't participate
    df = df.fillna('-')
    
    return df

def generate_markdown_table(df: pd.DataFrame, data: Dict) -> str:
    """Generate markdown table from DataFrame."""
    
    lines = []
    lines.append("# 2025 Wednesday Night Racing - Final Results")
    lines.append("")
    lines.append("This table shows each boat's performance across all race weeks.")
    lines.append("Format: Position(Score) or Status(Score) where Status = DNC/DSQ/DNF")
    lines.append("")
    
    # Get standings for additional context
    standings = data['series'].get('standings', [])
    if standings:
        lines.append("## Series Standings")
        lines.append("")
        lines.append("Final standings with throwouts applied:")
        lines.append("")
        lines.append("| Rank | Boat | Races | Net Score |")
        lines.append("|---:|---|---:|---:|")
        
        for i, standing in enumerate(standings, 1):
            boat = standing['boat'].title()
            races = standing['races']
            net = standing['net']
            lines.append(f"| {i} | {boat} | {races} | {net} |")
        
        lines.append("")
    
    lines.append("## Race-by-Race Results")
    lines.append("")
    
    # Create the main results table
    # Header row with boat names
    header = "| Boat |"
    separator = "|---|"
    
    for col in df.columns:
        # Format date nicely
        try:
            from datetime import datetime
            date_obj = datetime.strptime(col, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m/%d')
        except:
            formatted_date = col
        header += f" {formatted_date} |"
        separator += "---:|"
    
    lines.append(header)
    lines.append(separator)
    
    # Data rows
    for boat in df.index:
        # Clean up boat name for display
        display_boat = boat.replace('_', ' ').title()
        row = f"| {display_boat} |"
        
        for col in df.columns:
            value = df.loc[boat, col]
            row += f" {value} |"
        
        lines.append(row)
    
    lines.append("")
    lines.append("## Legend")
    lines.append("")
    lines.append("- **Position(Score)**: Finish position with points scored")
    lines.append("- **DNC(Score)**: Did Not Compete - boat registered for series but absent")  
    lines.append("- **DSQ(Score)**: Disqualified")
    lines.append("- **DNF(Score)**: Did Not Finish")
    lines.append("- **-**: Boat not yet registered for series at time of race")
    lines.append("")
    
    scoring_info = data['series'].get('scoring', {})
    if scoring_info:
        lines.append("## Scoring System")
        lines.append("")
        lines.append(f"- **System**: {scoring_info.get('system', 'Low Point')}")
        lines.append(f"- **Novice Credit**: {scoring_info.get('novice_credit', 'Not specified')}")
        lines.append(f"- **DNC Penalty**: {scoring_info.get('dnc_penalty', 'Not specified')}")
        lines.append(f"- **Throwouts**: {scoring_info.get('throwouts', 'Not specified')}")
        lines.append("")
    
    lines.append(f"Generated from results.json containing {len(data['series']['weeks'])} race weeks.")
    
    return "\n".join(lines)

def main():
    """Main function to generate final results."""
    print("Loading results data...")
    data = load_results_data()
    
    print("Creating results table...")
    df = create_results_table(data)
    
    print(f"Generated table with {len(df)} boats and {len(df.columns)} races")
    
    print("Generating markdown...")
    markdown = generate_markdown_table(df, data)
    
    # Write to file
    output_file = 'final_results.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"Final results written to {output_file}")
    print(f"Table dimensions: {len(df)} boats × {len(df.columns)} races")

if __name__ == "__main__":
    main()