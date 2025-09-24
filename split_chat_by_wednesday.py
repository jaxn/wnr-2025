#!/usr/bin/env python3
"""Split the master _chat.txt into multiple files, each starting on a Wednesday.

Output files are named YYYY-MM-DD.chat.txt where the date is the Wednesday
date of the first message contained in that segment. The split is based on
message timestamps in the WhatsApp export format: [M/D/YY, H:MM:SS AM/PM] ...

Only the lines from the first encountered Wednesday onward are split; any
pre-Wednesday preamble (e.g., group creation, adds) preceding the first
Wednesday is omitted from the segmented files per user instruction that each
file should start on a Wednesday.
"""

from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
import glob

CHAT_FILE = Path('_chat.txt')
DATE_PATTERN = re.compile(r'^\[(\d{1,2})/(\d{1,2})/(\d{2}), (\d{1,2}:\d{2}:\d{2})\s*([AP]M)\]')

def parse_timestamp(line: str) -> datetime | None:
    m = DATE_PATTERN.match(line)
    if not m:
        return None
    month, day, year2, timestr, ampm = m.groups()
    timestr_full = f"{timestr} {ampm}"
    try:
        dt = datetime.strptime(f"{month}/{day}/{year2} {timestr_full}", "%m/%d/%y %I:%M:%S %p")
        return dt
    except ValueError:
        return None

def main():
    if not CHAT_FILE.exists():
        raise SystemExit("_chat.txt not found")

    # Clean up previously generated segment files (pattern YYYY-MM-DD.chat.txt)
    for path in glob.glob('20??-??-??.chat.txt'):
        try:
            Path(path).unlink()
        except OSError:
            pass

    lines = CHAT_FILE.read_text(encoding='utf-8').splitlines(keepends=True)

    current_wed_date: datetime | None = None  # datetime of the Wednesday that started current segment
    current_segment_start_date: datetime | None = None  # date() of current Wednesday anchor
    buffer: list[str] = []
    created: list[str] = []

    def flush():
        nonlocal buffer, current_wed_date
        if current_wed_date and buffer:
            out_name = current_wed_date.strftime('%Y-%m-%d') + '.chat.txt'
            Path(out_name).write_text(''.join(buffer), encoding='utf-8')
            created.append(out_name)
        buffer = []

    for line in lines:
        dt = parse_timestamp(line)
        if dt:
            if dt.weekday() == 2:  # It's a Wednesday message
                # If it's a new Wednesday date (distinct from current)
                if current_segment_start_date is None or dt.date() != current_segment_start_date:
                    flush()
                    current_wed_date = dt
                    current_segment_start_date = dt.date()
            # We record lines only once we've started a Wednesday segment
            if current_segment_start_date is not None:
                buffer.append(line)
        else:
            # Non-timestamp continuation lines belong to current segment if started
            if current_segment_start_date is not None:
                buffer.append(line)

    flush()

    print(f"Created {len(created)} Wednesday chat segment files:")
    for name in created:
        print(f"  {name}")

if __name__ == '__main__':
    main()
