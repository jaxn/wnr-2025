#!/usr/bin/env python3
"""
Generate final results table for WNR 2025 series.
Creates a final_results.md file with a table where each row is a boat 
and each column is a week's race.
Reads data from per-week markdown files in results/ directory.
"""

import os
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime

def load_results_from_markdown_files(results_dir: str = 'results') -> Dict:
    """Load race results from per-week markdown files."""
    results_data = {}
    
    # Find all markdown files in results directory
    md_files = [f for f in os.listdir(results_dir) if f.endswith('.md') and re.match(r'\d{4}-\d{2}-\d{2}\.md', f)]
    md_files.sort()
    
    for md_file in md_files:
        date = md_file.replace('.md', '')
        filepath = os.path.join(results_dir, md_file)
        
        try:
            race_results = parse_markdown_results(filepath, date)
            if race_results:
                results_data[date] = race_results
        except Exception as e:
            print(f"Warning: Could not parse {md_file}: {e}")
            
    return results_data

def parse_markdown_results(filepath: str, date: str) -> Optional[Dict]:
    """Parse results from a single markdown file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the Summary section and the table after it
    # Look for "## Summary" followed by a table
    summary_match = re.search(r'## Summary.*?\n(.*?)(?=\n##|\n$)', content, re.DOTALL)
    
    if not summary_match:
        return None
    
    summary_content = summary_match.group(1)
    
    # Find the table within the summary content
    # Look for table header with Pos, Boat, etc.
    table_match = re.search(r'\| Pos \| Boat \| Range \| Novices \| Status \| Score \|.*?\n\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\n((?:\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*\n?)*)', summary_content, re.MULTILINE)
    
    if not table_match:
        return None
    
    results = []
    table_content = table_match.group(1)
    
    for line in table_content.strip().split('\n'):
        if not line.strip() or not line.startswith('|'):
            continue
            
        parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove empty first/last parts
        if len(parts) >= 6:
            try:
                pos_str = parts[0].strip()
                boat = parts[1].strip()
                range_str = parts[2].strip()
                novices_str = parts[3].strip()
                status = parts[4].strip()
                score_str = parts[5].strip()
                
                # Handle position - could be a number or "?"
                pos = int(pos_str) if pos_str.isdigit() else None
                
                # Handle novices
                novices = int(novices_str) if novices_str.isdigit() else 0
                
                # Handle score
                score = int(score_str) if score_str.isdigit() else None
                
                if boat and score is not None:
                    results.append({
                        'boat': boat,
                        'pos': pos,
                        'range': range_str,
                        'novices': novices,
                        'status': status,
                        'score': score
                    })
            except (ValueError, IndexError):
                continue
    
    return {
        'date': date,
        'results': results
    } if results else None

def create_results_table(results_data: Dict) -> pd.DataFrame:
    """Create a DataFrame with boats as rows and race weeks as columns."""
    
    # Get all boats and race dates
    all_boats = set()
    race_dates = sorted(results_data.keys())
    
    # Collect all boat names from all races and normalize case
    boat_name_mapping = {}  # Maps lowercase to proper case name
    for race_data in results_data.values():
        for result in race_data['results']:
            boat_name = result['boat']
            boat_lower = boat_name.lower()
            
            # Use the first occurrence as the canonical name, or prefer proper case
            if boat_lower not in boat_name_mapping:
                boat_name_mapping[boat_lower] = boat_name
            else:
                # If we have a version with proper capitalization, prefer it
                existing = boat_name_mapping[boat_lower]
                if boat_name != existing:
                    # Choose the one with more capitals (better formatting)
                    if sum(1 for c in boat_name if c.isupper()) > sum(1 for c in existing if c.isupper()):
                        boat_name_mapping[boat_lower] = boat_name
    
    all_boats = sorted(boat_name_mapping.values())
    
    # Create a DataFrame with boats as index and race dates as columns
    df = pd.DataFrame(index=all_boats, columns=race_dates)
    
    # Fill in the scores for each boat in each race
    for date, race_data in results_data.items():
        for result in race_data['results']:
            # Normalize boat name to canonical version
            boat_lower = result['boat'].lower()
            canonical_boat = boat_name_mapping[boat_lower]
            
            pos = result.get('pos')
            score = result.get('score', '')
            status = result.get('status', 'FIN')
            
            # Format the display value
            if status == 'DNC':
                df.loc[canonical_boat, date] = f"DNC({score})"
            elif status == 'DSQ':
                df.loc[canonical_boat, date] = f"DSQ({score})"
            elif status == 'DNF':
                df.loc[canonical_boat, date] = f"DNF({score})"
            elif pos is not None:
                df.loc[canonical_boat, date] = f"{pos}({score})"
            else:
                df.loc[canonical_boat, date] = str(score) if score != '' else 'DNC'
    
    # Fill NaN values with 'DNC' for races where boat didn't participate
    df = df.fillna('DNC')
    
    return df

def generate_markdown_table(df: pd.DataFrame, results_data: Dict) -> str:
    """Generate markdown table from DataFrame."""
    
    lines = []
    lines.append("# 2025 Wednesday Night Racing - Final Results")
    lines.append("")
    lines.append("<!-- markdownlint-disable MD013 -->")
    lines.append("")
    lines.append("This table shows each boat's performance across all race weeks.")
    lines.append("Format: Position(Score) or Status(Score) where Status = DNC/DSQ/DNF")
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
        # Use boat name as-is from markdown files (proper capitalization)
        row = f"| {boat} |"
        
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
    lines.append("- **DNC**: Boat did not participate in this race")
    lines.append("")
    
    lines.append("## Scoring System")
    lines.append("")
    lines.append("- **System**: Low Point")
    lines.append("- **Novice Credit**: Points = max(1, finish_position - min(2, novice_count))")
    lines.append("- **DNC/DSQ/DNF Penalty**: Varies by race")
    lines.append("- **Throwouts**: 1 worst per 4 races (series rule)")
    lines.append("")
    
    lines.append(f"Generated from {len(results_data)} per-week markdown files in results/ directory.")
    lines.append("")
    
    return "\n".join(lines)

def main():
    """Main function to generate final results."""
    print("Loading results from per-week markdown files...")
    results_data = load_results_from_markdown_files()
    
    if not results_data:
        print("Error: No results data found in markdown files")
        return
    
    print(f"Found {len(results_data)} race weeks")
    
    print("Creating results table...")
    df = create_results_table(results_data)
    
    print(f"Generated table with {len(df)} boats and {len(df.columns)} races")
    
    print("Generating markdown...")
    markdown = generate_markdown_table(df, results_data)
    
    # Write markdown file
    output_file_md = 'final_results.md'
    with open(output_file_md, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"Final results written to {output_file_md}")
    
    # Write CSV file
    output_file_csv = 'final_results.csv'
    # Add boat name as first column for CSV
    df_csv = df.copy()
    df_csv.insert(0, 'Boat', df_csv.index)
    df_csv.to_csv(output_file_csv, index=False)
    print(f"Final results written to {output_file_csv}")
    
    print(f"Table dimensions: {len(df)} boats × {len(df.columns)} races")

if __name__ == "__main__":
    main()