# WNR 2025 - Wednesday Night Racing Results Repository

ALWAYS follow these instructions first and only fallback to additional search
and context gathering if the information in these instructions is incomplete
or found to be in error.

## Repository Overview

This repository manages data and documentation for Percy Priest Yacht Club's
2025 Wednesday Night Racing (WNR) series. The primary data source is WhatsApp
chat exports containing race results, with additional documentation about
sailing procedures and scoring rules.

## Working Effectively

### Environment Setup

- Python 3.12+ is available at `/usr/bin/python3`
- Node.js v20+ and npm are available
- Git is available for version control
- Required packages installation:
  - `pip install pandas numpy` - NEVER CANCEL: takes 2-3 minutes for
    data analysis
  - `npm install -g markdownlint-cli` - NEVER CANCEL: takes 1-2 minutes
    for markdown validation

### Core Commands - VALIDATED TO WORK

- **Lint markdown files**: `markdownlint *.md` - takes 5-10 seconds
- **Process chat data**: `python3 -c "import pandas as pd; print('Data
  processing ready')"` - takes 2-3 seconds
- **Validate repository structure**: `ls -la` and `find . -name "*.md"` -
  instant
- **Check git status**: `git status` - instant

## Repository Structure

```text
/
├── .github/
│   └── instructions/
│       └── chat-instructions.md    # AI parsing instructions for chat data
├── README.md                       # Main repository documentation
├── wnr-sailing-instructions.md     # 2024 sailing rules and procedures
├── _chat.txt                       # WhatsApp export with race data (1138 lines)
└── PPYC_Burgee_400ppi.tif         # Club logo image (20MB TIFF file)
```

## Data Processing and Analysis

### Primary Data Source

- **_chat.txt**: WhatsApp chat export containing race communications and results
- **Format**: `[MM/DD/YY, HH:MM:SS AM/PM] Author: Message`
- **Content**: Race results, crew coordination, weather decisions, finish positions
- **Size**: 1138 lines, ~90KB text file

### Data Processing Guidelines

- Use Python with pandas for data analysis: `python3 -c "import pandas as pd;
  import re"`
- Race results are embedded in chat messages using patterns like:
  - "Boat X ahead", "Boat Y behind"
  - "1st Boat A, 2nd Boat B, 3rd Boat C"
  - Novice crew counts: "X novices on board"
- Parse timestamps to group messages by race date (Wednesdays)
- ALWAYS validate extracted data against multiple message sources

### Sample Data Processing

```python
# Tested and working example
import re
with open('_chat.txt', 'r') as f:
    content = f.read()
    
# Extract race finish patterns
finish_patterns = [
    r'(\w+)\s+ahead',
    r'(\w+)\s+behind', 
    r'1st\s+(\w+)',
    r'(\d+)(?:st|nd|rd|th)\s+(\w+)'
]

# This yields ~155 race result mentions across the season
```

## Validation and Quality Assurance

### Markdown Validation

- **ALWAYS run before committing**: `markdownlint *.md`
- **Common issues**: Line length (80 char limit), blank lines around lists
- **Time**: Takes 5-10 seconds, NEVER CANCEL
- **Exit codes**: 0 = clean, 1 = warnings/errors found

### Data Validation

- **Chat data integrity**: Check file size ~90KB, 1138 lines: `wc -l _chat.txt`
- **Race result extraction**: Verify ~155 finish mentions found
- **Date range**: 2025 season data from March through September
- **Manual validation**: Cross-reference multiple messages for same race

### Testing Scenarios

After making changes to processing scripts or documentation:

1. **Markdown validation**: Run `markdownlint *.md` and fix any issues
2. **Data processing test**:

   ```bash
   python3 -c "
   import pandas as pd
   with open('_chat.txt', 'r') as f:
       lines = f.readlines()
   print(f'Chat file: {len(lines)} lines')
   assert len(lines) > 1000, 'Chat data incomplete'
   print('Data validation: PASSED')
   "
   ```

3. **Repository structure**: Verify all expected files present:
   `find . -name "*.md" | wc -l` should return 3+

## External Dependencies and References

### Live Data Sources

- **PHRF ratings spreadsheet**:
  <https://docs.google.com/spreadsheets/u/1/d/1F1ffFLq7Por_dJC3XpFjAxr8sW9DvRH1nTcEvw86ex8/htmlview#gid=2004385695>
- **PPYC pursuit start times**:
  <https://ppyc.clubexpress.com/docs.ashx?id=780451>
- **Official time source**: <https://www.time.gov/>

### Club Information

- **Location**: Percy Priest Lake, Nashville, Tennessee
- **Race format**: Pursuit racing with PHRF handicap system
- **Schedule**: Wednesday evenings during sailing season
- **Organizer**: Percy Priest Yacht Club (PPYC)

## Common Tasks and Workflows

### Parsing New Race Results

1. **Extract chat data**: Race results typically posted Wednesday evenings
   7-10 PM
2. **Identify finish order**: Look for "ahead/behind" statements and position
   lists
3. **Count novice crew**: Search for "X novices" or "novice" mentions per boat
4. **Apply scoring rules**: Low-point system with novice bonuses (detailed in
   chat-instructions.md)
5. **Cross-validate**: Verify results against multiple message sources

### Updating Documentation

1. **Edit markdown files** using standard text editors
2. **Validate syntax**: Run `markdownlint filename.md`
3. **Fix common issues**: Line length, list formatting, heading structure
4. **Test links**: Verify external URLs still work (sailing instructions,
   PPYC resources)

### Git Workflow

- **Check status**: `git status` (instant)
- **Stage changes**: `git add filename.md`
- **Commit**: `git commit -m "descriptive message"`
- **Check history**: `git log --oneline -10`

## Timing Expectations

| Command | Expected Time | Timeout Setting |
|---------|---------------|-----------------|
| `markdownlint *.md` | 5-10 seconds | 30 seconds |
| `pip install pandas` | 2-3 minutes | 5 minutes |
| `npm install -g markdownlint-cli` | 1-2 minutes | 3 minutes |
| Python data processing | 2-5 seconds | 30 seconds |
| Git operations | <1 second | 10 seconds |

**NEVER CANCEL** any installation or processing commands. Package installations
may appear to hang but are downloading dependencies.

## File Locations and Key Content

### Documentation Files

- **README.md**: Repository overview and purpose
- **wnr-sailing-instructions.md**: Detailed sailing rules, scoring system,
  race procedures
- **.github/instructions/chat-instructions.md**: Comprehensive AI parsing
  instructions for race data

### Important Data Sections

- **Boat aliases**: Dawg ≡ Scalded Dawg, Psycho Killer ≡ J-80, etc.
- **Scoring rules**: Low-point system, novice bonuses, drop races
- **Race timing**: 6:00 PM pursuit starts, Wednesday evenings
- **Course variations**: Standard vs. short course, reverse course first
  Wednesday of month

### Frequently Referenced Information

- **Boat names**: Danger Zone, Ambush, Scooter, Go Hogs Go, Fast Freddy,
  Wizard, Dawg, Psycho Killer, Itch, Sweet Virginia, Dandelion, Caper
- **Race Directors**: Jackson (primary), Sam Beckman (backup)
- **Common race formats**: Pursuit start with PHRF handicaps
- **Weather factors**: Thunderstorms cause cancellations, light wind triggers
  short course

## Validation Requirements

Before completing any task:

1. **Run markdown linting**: `markdownlint *.md` - must return clean or
   document issues
2. **Verify data integrity**: Chat file size and line count unchanged unless
   intentionally modified
3. **Test data processing**: Ensure Python/pandas operations complete
   successfully
4. **Check external links**: Verify PPYC URLs and Google Sheets links still
   accessible
5. **Validate against instructions**: Cross-reference changes with existing
   chat-instructions.md

## Error Handling and Troubleshooting

### Common Issues

- **Markdown lint failures**: Usually line length or list formatting - fix
  and re-run
- **Python import errors**: Install pandas/numpy if missing -
  `pip install pandas numpy`
- **Chat data parsing errors**: Check for encoding issues or truncated file
- **Git conflicts**: Repository is primarily documentation, conflicts rare

### When Instructions Are Insufficient

Only search for additional information or run exploratory bash commands when:

- These instructions contradict observed behavior
- New file types or tools are encountered not covered here
- External dependencies change (broken links, API changes)
- Data format changes significantly from described patterns

Always document any new findings to update these instructions for future use.
