# WNR 2025 Racing Data Repository

This repository manages race data for PPYC's (Percy Priest Yacht Club) Wednesday Night Racing 2025 series. The primary function is parsing race results from WhatsApp chat logs and publishing standings for the sailing competition.

**ALWAYS reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Repository Structure
- **_chat.txt** (1,138 lines) - WhatsApp chat logs containing race coordination and results
- **wnr-sailing-instructions.md** (75 lines) - Official sailing instructions for the 2025 season  
- **README.md** (21 lines) - Basic repository information
- **No build system, package managers, or complex dependencies required**

### Available Tools and Setup
- **Python 3.12.3** - Primary tool for data processing (VALIDATED)
- **Node.js 20.19.5** - Alternative for JavaScript processing (VALIDATED)
- **Standard Unix tools** - grep, sed, awk, etc. for text processing
- **No installation required** - All necessary tools are pre-installed

### Core Operations (All Timings Validated)

#### Parse Race Results from Chat Data
```bash
python3 -c "
import re
with open('_chat.txt', 'r', encoding='utf-8') as f:
    content = f.read()
# Find the specific race result line format
race_line = [line for line in content.split('\n') if '1st' in line and '2nd' in line and 'Danger Zone' in line]
if race_line:
    results = re.findall(r'(\d+(?:st|nd|rd|th))\s+([^,]+)', race_line[0])
    for position, boat in results:
        print(f'{position}: {boat.strip()}')
else:
    print('No complete race results found')
"
```
**Timing: <0.1 seconds. NEVER CANCEL. Expected output: 7 boat positions.**

#### Extract Boat Position Reports  
```bash
python3 -c "
import re
with open('_chat.txt', 'r', encoding='utf-8') as f:
    content = f.read()
positions = re.findall(r'([A-Za-z\s]+)\s+ahead.*?([A-Za-z\s]+)\s+behind', content, re.IGNORECASE)
print(f'Found {len(positions)} position reports')
"
```
**Timing: <0.1 seconds. NEVER CANCEL.**

#### Generate JSON Race Report
```bash
python3 -c "
import json
import re
with open('_chat.txt', 'r', encoding='utf-8') as f:
    content = f.read()
# Find the specific race result line format
race_line = [line for line in content.split('\n') if '1st' in line and '2nd' in line and 'Danger Zone' in line]
if race_line:
    results = re.findall(r'(\d+(?:st|nd|rd|th))\s+([^,]+)', race_line[0])
    standings = [{'position': pos, 'boat_name': boat.strip(), 'points': i+1} 
                 for i, (pos, boat) in enumerate(results)]
    with open('race_standings.json', 'w') as f:
        json.dump(standings, f, indent=2)
    print(f'Generated standings for {len(standings)} boats')
else:
    print('No race results found to process')
"
```
**Timing: <0.1 seconds. NEVER CANCEL. Expected output: "Generated standings for 7 boats"**

#### Generate HTML Race Results
```bash
python3 -c "
import re
from datetime import datetime
with open('_chat.txt', 'r', encoding='utf-8') as f:
    content = f.read()
# Find the specific race result line format
race_line = [line for line in content.split('\n') if '1st' in line and '2nd' in line and 'Danger Zone' in line]
if race_line:
    results = re.findall(r'(\d+(?:st|nd|rd|th))\s+([^,]+)', race_line[0])
    html = '''<!DOCTYPE html>
<html><head><title>WNR 2025 Results</title></head><body>
<h1>PPYC Wednesday Night Racing 2025</h1><table border=\"1\">
<tr><th>Position</th><th>Boat Name</th></tr>'''
    for pos, boat in results:
        html += f'<tr><td>{pos}</td><td>{boat.strip()}</td></tr>'
    html += f'</table><p>Generated: {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}</p></body></html>'
    with open('race_results.html', 'w') as f:
        f.write(html)
    print(f'HTML report generated with {len(results)} boats')
else:
    print('No race results found to process')
"
```
**Timing: <0.1 seconds. NEVER CANCEL. Expected output: "HTML report generated with 7 boats"**

## Validation Requirements

### ALWAYS Test These Scenarios After Making Changes
1. **Parse race results** - Run the race results parsing command and verify output format
2. **Extract boat names** - Confirm all participating boats are identified correctly
3. **Generate output files** - Verify JSON and HTML outputs are properly formatted
4. **Process documentation** - Ensure README.md and sailing instructions remain accessible

### Manual Validation Steps
```bash
# Test basic functionality
python3 -c "print('Python working'); import re, json; print('Required modules available')"

# Verify data integrity
wc -l README.md _chat.txt wnr-sailing-instructions.md

# Test file processing
head -5 _chat.txt | grep -E '\[[0-9]+/[0-9]+/[0-9]+,'
```

## Common Tasks

### Extract Specific Boat Data
```bash
grep -i "ambush\|danger zone\|dawg\|psyco\|scooter" _chat.txt | head -10
```

### Find Race Dates
```bash
grep -E '\[[0-9]+/[0-9]+/[0-9]+' _chat.txt | head -5
```

### Count Messages by Date
```bash
python3 -c "
import re
with open('_chat.txt', 'r', encoding='utf-8') as f:
    content = f.read()
dates = re.findall(r'\[(\d+/\d+/\d+),', content)
print(f'Found messages from {len(set(dates))} unique dates')
"
```

### View Repository Structure
```bash
ls -la
# Expected output:
# README.md (935 bytes)
# _chat.txt (90,450 bytes) 
# wnr-sailing-instructions.md (6,596 bytes)
```

## Key Boat Names in 2025 Series
Based on chat analysis, these boats actively participate:
- Ambush, Danger Zone, Dawg, Psyco Killer, Scooter
- Go Hogs Go, Fast Freddy, Itchin', Sweet Virginia
- Club J22, Wizard, Dandelion, Caper

## Expected Data Patterns

### Race Result Format
```
1st Danger Zone, 2nd Dawg, 3rd Psyco, 4th Scooter, 5th Ambush, 6th Go Hogs Go, 7th Fast Freddy
```

### Position Report Format  
```
[Date] Boat Name: Ambush ahead. Fast Freddy behind.
```

### Chat Message Format
```
[MM/DD/YY, HH:MM:SS AM/PM] Skipper Name: Message content
```

## Development Guidelines

- **Always process _chat.txt with UTF-8 encoding** to handle special characters
- **Use regex patterns for consistent parsing** - validated patterns are provided above
- **Generate both JSON and HTML outputs** for different consumption needs
- **Preserve original data** - never modify _chat.txt or sailing instructions
- **Test output formatting** before generating final reports
- **Include timestamps** in generated reports for tracking

## DO NOT Attempt
- Installing additional packages or dependencies (none needed)
- Modifying the core data files (_chat.txt, README.md, wnr-sailing-instructions.md)
- Complex database operations (simple file processing is sufficient)
- Network operations (this is an offline data processing repository)

## Troubleshooting

### If Python Scripts Fail
1. Check file encoding: `file _chat.txt` (should show UTF-8)
2. Verify Python availability: `python3 --version` (should show 3.12.3)
3. Test basic file reading: `python3 -c "open('_chat.txt').read()[:100]"`

### If Output Is Incorrect
1. Verify input data: `wc -l _chat.txt` (should show 1138 lines)
2. Check regex patterns match expected format
3. Validate with known results: Search for "1st Danger Zone" in chat

This repository is optimized for quick, reliable processing of sailing race data with minimal setup and maximum reliability.