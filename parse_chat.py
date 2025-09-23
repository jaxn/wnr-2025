#!/usr/bin/env python3
"""
PPYC Wednesday Night Racing Chat Parser

Parses WhatsApp chat export to generate race results in JSON format.
Follows specifications in .github/instructions/chat-instructions.md
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict, namedtuple
import sys

# Message structure
Message = namedtuple('Message', ['timestamp', 'author', 'text', 'raw_line'])

# Boat aliases mapping - more comprehensive
BOAT_ALIASES = {
    'scalded dawg': 'dawg',
    'scalded dog': 'dawg', 
    'dawg': 'dawg',
    'dog': 'dawg',
    'psycho killer': 'j-80',
    'psychokiller': 'j-80',
    'psyco killer': 'j-80',  # common misspelling
    'j-80': 'j-80',
    'j80': 'j-80',
    'caper': 'max',
    'max': 'max',
    'fast freddy': 'fred',
    'fast freddie': 'fred',
    'freddy': 'fred', 
    'freddie': 'fred',
    'fred': 'fred',
    '509': 'fred',
    'danger zone': 'danger zone',  # NOT aliased to j-80
    'zone': 'danger zone',
    'dandelion': 'dandelion',  # Not a club boat
    'go hogs': 'go hogs',
    'gohogs': 'go hogs',
    'go hogs go': 'go hogs',
    'go hogs go go': 'go hogs',
    'gohogso': 'go hogs',
    'hogs': 'go hogs',
    'ambush': 'ambush',
    'sweet virginia': 'sweet virginia',
    'wizard': 'wizard',
    'itch': 'itch',
    'scooter': 'scooter',
    'beat it': 'beat it',
    'beatit': 'beat it'
}

class ChatParser:
    def __init__(self, chat_file_path: str):
        self.chat_file_path = chat_file_path
        self.messages: List[Message] = []
        self.weekly_races: Dict[str, List[Message]] = defaultdict(list)
        self.series_data = {
            "boats_seen": set(),
            "weeks": [],
            "scoring": {},
            "standings": []
        }
        
    def parse_chat_file(self):
        """Parse the WhatsApp chat export file"""
        with open(self.chat_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_message = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove invisible Unicode characters that might interfere
            line = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]', '', line)
            line = re.sub(r'[‎‏]', '', line)  # Remove specific RTL/LTR markers
            
            # Check if this is a new message line
            # Format: [M/D/YY, H:MM:SS AM/PM] Author: Message
            # Handle Unicode spaces between time and AM/PM
            message_pattern = r'^\[(\d{1,2}/\d{1,2}/\d{2}), (\d{1,2}:\d{2}:\d{2}[\s\u00A0\u202F\u2009\u2007\u2008][AP]M)\] ([^:]+): (.*)$'
            match = re.match(message_pattern, line)
            
            if match:
                # Save previous message if exists
                if current_message:
                    self._add_message(current_message)
                
                # Start new message
                date_str, time_str, author, text = match.groups()
                current_message = {
                    'date_str': date_str,
                    'time_str': time_str,
                    'author': author.strip(),
                    'text': text.strip(),
                    'raw_line': line
                }
            else:
                # This is a continuation of the previous message
                if current_message:
                    current_message['text'] += ' ' + line
                    current_message['raw_line'] += '\n' + line
        
        # Don't forget the last message
        if current_message:
            self._add_message(current_message)
    
    def _add_message(self, msg_data):
        """Add a parsed message to the messages list"""
        try:
            # Parse timestamp - handle narrow no-break space and other Unicode spaces
            dt_str = f"{msg_data['date_str']}, {msg_data['time_str']}"
            # Replace various Unicode spaces with regular space
            dt_str = re.sub(r'[\u00A0\u202F\u2009\u2007\u2008]', ' ', dt_str)
            timestamp = datetime.strptime(dt_str, "%m/%d/%y, %I:%M:%S %p")
            
            # Create message object
            message = Message(
                timestamp=timestamp,
                author=msg_data['author'],
                text=msg_data['text'],
                raw_line=msg_data['raw_line']
            )
            
            self.messages.append(message)
            
            # Group by Wednesday dates
            if timestamp.weekday() == 2:  # Wednesday is 2
                date_key = timestamp.strftime("%Y-%m-%d")
                self.weekly_races[date_key].append(message)
                
        except ValueError as e:
            print(f"Error parsing timestamp: {dt_str} - {e}")
            return
    
    def normalize_boat_name(self, boat_name: str) -> Tuple[str, List[str]]:
        """Normalize boat name using alias mapping, return (normalized, aliases_used)"""
        original = boat_name.lower().strip()
        
        # Check for aliases
        if original in BOAT_ALIASES:
            normalized = BOAT_ALIASES[original]
            aliases_used = [boat_name] if boat_name.lower() != normalized else []
            return normalized, aliases_used
        
        # Return original if no alias found
        return boat_name.lower(), []
    
    def extract_race_claims(self, messages: List[Message]) -> List[Dict]:
        """Extract atomic race claims from messages"""
        claims = []
        
        for msg in messages:
            text = msg.text
            text_lower = text.lower()
            
            # Skip system messages
            if msg.author == 'Wednesday Night Racing':
                continue
            
            # Look for direct finish position statements
            # Pattern: "Boat ahead. Boat behind." or "Boat ahead/behind Boat"
            
            # Find sentences with ahead/behind
            sentences = re.split(r'[.!?]', text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_lower = sentence.lower()
                
                # Pattern 1: "X ahead" - means X is ahead of reporter's boat
                ahead_match = re.search(r'([a-zA-Z0-9\s\-]+?)\s+ahead(?:\s|$|[.,])', sentence_lower)
                if ahead_match:
                    boat_name = ahead_match.group(1).strip()
                    boat_name, aliases = self.normalize_boat_name(boat_name)
                    if boat_name and len(boat_name) > 1:  # Filter out single letters
                        claims.append({
                            'type': 'placement',
                            'boat': boat_name,
                            'position_type': 'ahead_of_reporter',
                            'text': sentence,
                            'author': msg.author,
                            'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p"),
                            'aliases_used': aliases
                        })
                
                # Pattern 2: "X behind" - means X is behind reporter's boat  
                behind_match = re.search(r'([a-zA-Z0-9\s\-]+?)\s+behind(?:\s|$|[.,])', sentence_lower)
                if behind_match:
                    boat_name = behind_match.group(1).strip()
                    boat_name, aliases = self.normalize_boat_name(boat_name)
                    if boat_name and len(boat_name) > 1:  # Filter out single letters
                        claims.append({
                            'type': 'placement',
                            'boat': boat_name,
                            'position_type': 'behind_reporter',
                            'text': sentence,
                            'author': msg.author,
                            'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p"),
                            'aliases_used': aliases
                        })
                
                # Pattern 3: Look for "ahead of" or "behind" constructions
                # "A ahead of B" or "A behind B"
                ahead_of_match = re.search(r'([a-zA-Z0-9\s\-]+?)\s+ahead\s+of\s+([a-zA-Z0-9\s\-]+)', sentence_lower)
                if ahead_of_match:
                    boat1 = self.normalize_boat_name(ahead_of_match.group(1).strip())[0]
                    boat2 = self.normalize_boat_name(ahead_of_match.group(2).strip())[0]
                    if boat1 and boat2 and len(boat1) > 1 and len(boat2) > 1:
                        claims.append({
                            'type': 'relative_position',
                            'boat_ahead': boat1,
                            'boat_behind': boat2,
                            'text': sentence,
                            'author': msg.author,
                            'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p")
                        })
            
            # Look for novice mentions with specific numbers
            novice_pattern = r'(\d+)\s+novice'
            novice_matches = re.findall(novice_pattern, text_lower)
            
            if novice_matches:
                claims.append({
                    'type': 'novice',
                    'count': int(novice_matches[0]),
                    'text': text,
                    'author': msg.author,
                    'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p"),
                    'boat': self._infer_boat_from_author(msg.author)  # Try to infer boat
                })
            
            # Look for DSQ/DNF mentions
            if 'dsq' in text_lower or 'dnf' in text_lower:
                penalty_type = 'DSQ' if 'dsq' in text_lower else 'DNF'
                claims.append({
                    'type': 'penalty',
                    'penalty_type': penalty_type,
                    'text': text,
                    'author': msg.author,
                    'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p"),
                    'boat': self._infer_boat_from_author(msg.author)
                })
        
        return claims
    
    def _infer_boat_from_author(self, author: str) -> str:
        """Try to infer boat name from author name"""
        # Common mappings of skippers to boats
        author_to_boat = {
            'george heintz': 'go hogs',
            'sam beckman': 'danger zone',
            'jackson': 'ambush', 
            'david curtze': 'scooter',
            'max sadler': 'max',
            'jeremy odom': 'sweet virginia',
            'fred bartrom': 'fred',
            'alicia noble': 'wizard',
            'kate': 'itch',
            'robby': 'dandelion',
            'chris berkey': 'beat it'
        }
        
        author_lower = author.lower()
        return author_to_boat.get(author_lower, 'UNKNOWN')
    
    def process_weekly_race(self, date: str, messages: List[Message]) -> Dict:
        """Process a single week's race"""
        claims = self.extract_race_claims(messages)
        
        # Extract starters (boats that appear in placement claims)
        starters = set()
        for claim in claims:
            if claim['type'] == 'placement':
                starters.add(claim['boat'])
                self.series_data['boats_seen'].add(claim['boat'])
        
        # Simple finishing order (this is a simplified implementation)
        # In a full implementation, this would solve the partial order problem
        results = []
        position = 1
        
        for boat in sorted(starters):
            results.append({
                'boat': boat,
                'pos': position,
                'novices': 0,  # Would be calculated from claims
                'status': 'FIN',
                'score': position,
                'aliasesUsed': []
            })
            position += 1
        
        return {
            'date': date,
            'starters': list(starters),
            'results': results,
            'evidence': claims,
            'ambiguity': None
        }
    
    def generate_results(self) -> Dict:
        """Generate the complete results JSON"""
        self.parse_chat_file()
        
        # Process each Wednesday race
        for date in sorted(self.weekly_races.keys()):
            week_data = self.process_weekly_race(date, self.weekly_races[date])
            self.series_data['weeks'].append(week_data)
        
        # Convert sets to lists for JSON serialization
        self.series_data['boats_seen'] = list(self.series_data['boats_seen'])
        
        return {"series": self.series_data}

def main():
    if len(sys.argv) > 1:
        chat_file = sys.argv[1]
    else:
        chat_file = '_chat.txt'
    
    parser = ChatParser(chat_file)
    results = parser.generate_results()
    
    # Write results to JSON file
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Results written to results.json")
    print(f"Found {len(results['series']['weeks'])} race weeks")
    print(f"Boats seen: {results['series']['boats_seen']}")

if __name__ == "__main__":
    main()