#!/usr/bin/env python3
"""
Enhanced PPYC Wednesday Night Racing Chat Parser

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

def load_boat_mappings(boats_json_path: str = 'boats.json') -> Tuple[Dict[str, str], Dict[str, str]]:
    """Load boat aliases and author-to-boat mappings from JSON file"""
    try:
        with open(boats_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['boat_aliases'], data['author_to_boat']
    except FileNotFoundError:
        print(f"Warning: {boats_json_path} not found. Using empty mappings.")
        return {}, {}
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error loading {boats_json_path}: {e}")
        return {}, {}

class EnhancedChatParser:
    def __init__(self, chat_file_path: str, boats_json_path: str = 'boats.json'):
        self.chat_file_path = chat_file_path
        self.boat_aliases, self.author_to_boat = load_boat_mappings(boats_json_path)
        self.messages: List[Message] = []
        self.weekly_races: Dict[str, List[Message]] = defaultdict(list)
        self.series_data = {
            "boats_seen": set(),
            "weeks": [],
            "scoring": {
                "system": "Low Point",
                "novice_credit": "max(1, finish_position - min(2, novice_count))",
                "dsq_dnf_penalty": "starters + 1", 
                "dnc_penalty": "boats_in_series + 1",
                "throwouts": "1 worst per 4 races"
            },
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
        if not boat_name:
            return "", []
            
        original = boat_name.lower().strip()
        
        # Handle common misspellings and variations
        original = re.sub(r'\s+', ' ', original)  # Normalize whitespace
        
        # Check for aliases
        if original in self.boat_aliases:
            normalized = self.boat_aliases[original]
            aliases_used = [boat_name] if boat_name.lower() != normalized else []
            return normalized, aliases_used
        
        # Check for partial matches for boats with common misspellings
        if 'psyco' in original or 'psycho' in original:
            return 'psycho killer', [boat_name]
        elif 'danger' in original and 'zone' in original:
            return 'danger zone', [boat_name] if original != 'danger zone' else []
        elif 'go hogs' in original or 'gohogs' in original or (original == 'hogs' and 'go' not in original):
            return 'go hogs go', [boat_name] if original != 'go hogs go' else []
        elif 'fast fred' in original or original == 'fred':
            return 'fred', [boat_name] if original != 'fred' else []
        elif 'sweet virginia' in original:
            return 'sweet virginia', [boat_name] if original != 'sweet virginia' else []
        elif original == 'max' or 'caper' in original:
            return 'caper', [boat_name] if original != 'caper' else []
        elif 'dawg' in original or original == 'dog':
            return 'scalded dawg', [boat_name] if original != 'scalded dawg' else []
        elif 'dandelion' in original:
            return 'dandelion', [boat_name] if original != 'dandelion' else []
        
        # Return original if no alias found, but clean it up
        cleaned = re.sub(r'[^a-zA-Z0-9\s\-]', '', original).strip()
        return cleaned if cleaned else original.lower(), []
    
    def extract_complete_finish_order(self, text: str) -> Optional[List[str]]:
        """Extract complete finish order from messages like '1st X, 2nd Y, 3rd Z...'"""
        # Pattern for numbered finish positions
        pattern = r'(\d+)(?:st|nd|rd|th)\s+([^,]+?)(?:,|$|\s+\d+(?:st|nd|rd|th))'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if len(matches) >= 3:  # At least 3 boats for a valid finish order
            finish_order = []
            for pos, boat_name in matches:
                boat_name = boat_name.strip()
                normalized_boat, _ = self.normalize_boat_name(boat_name)
                if normalized_boat:
                    finish_order.append((int(pos), normalized_boat))
            
            # Sort by position and return boat names
            finish_order.sort(key=lambda x: x[0])
            return [boat for pos, boat in finish_order]
        
        return None
    
    def extract_individual_claims(self, messages: List[Message]) -> List[Dict]:
        """Extract individual ahead/behind claims from messages"""
        claims = []
        
        for msg in messages:
            text = msg.text
            text_lower = text.lower()
            
            # Skip system messages and non-race messages during race time
            if msg.author == 'Wednesday Night Racing':
                continue
            
            # Skip messages that are clearly not finish reports (before race start)
            if msg.timestamp.hour < 19:  # Before 7 PM
                continue
            
            # Look for numbered finish order first
            complete_order = self.extract_complete_finish_order(text)
            if complete_order:
                claims.append({
                    'type': 'complete_finish_order',
                    'finish_order': complete_order,
                    'text': text,
                    'author': msg.author,
                    'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p")
                })
                continue
            
            # Look for simple finish reports like "Ambush ahead. Fast Freddy behind."
            # Pattern: "X ahead" followed by "Y behind" in same message or nearby
            sentences = re.split(r'[.!?]', text)
            
            author_boat = self.author_to_boat.get(msg.author.lower(), None)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_lower = sentence.lower()
                
                # Pattern: "X ahead" - X is ahead of the reporting boat
                ahead_match = re.search(r'([a-zA-Z0-9\s\-]+?)\s+ahead(?:\s|$|[.,])', sentence_lower)
                if ahead_match and author_boat:
                    boat_name = ahead_match.group(1).strip()
                    normalized_boat, aliases = self.normalize_boat_name(boat_name)
                    if normalized_boat and len(normalized_boat) > 1:
                        claims.append({
                            'type': 'relative_position',
                            'boat_ahead': normalized_boat,
                            'boat_behind': author_boat,
                            'text': sentence,
                            'author': msg.author,
                            'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p"),
                            'aliases_used': aliases
                        })
                
                # Pattern: "X behind" - X is behind the reporting boat
                behind_match = re.search(r'([a-zA-Z0-9\s\-]+?)\s+behind(?:\s|$|[.,])', sentence_lower)
                if behind_match and author_boat:
                    boat_name = behind_match.group(1).strip()
                    normalized_boat, aliases = self.normalize_boat_name(boat_name)
                    if normalized_boat and len(normalized_boat) > 1:
                        claims.append({
                            'type': 'relative_position',
                            'boat_ahead': author_boat,
                            'boat_behind': normalized_boat,
                            'text': sentence,
                            'author': msg.author,
                            'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p"),
                            'aliases_used': aliases
                        })
            
            # Look for novice mentions with numbers
            novice_pattern = r'(\d+)\s+novice'
            novice_matches = re.findall(novice_pattern, text_lower)
            
            if novice_matches:
                boat = self.author_to_boat.get(msg.author.lower(), 'UNKNOWN')
                claims.append({
                    'type': 'novice',
                    'boat': boat,
                    'count': int(novice_matches[0]),
                    'text': text,
                    'author': msg.author,
                    'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p")
                })
            
            # Look for DSQ/DNF mentions
            if 'dsq' in text_lower or 'dnf' in text_lower:
                penalty_type = 'DSQ' if 'dsq' in text_lower else 'DNF'
                boat = self.author_to_boat.get(msg.author.lower(), 'UNKNOWN')
                claims.append({
                    'type': 'penalty',
                    'boat': boat,
                    'penalty_type': penalty_type,
                    'text': text,
                    'author': msg.author,
                    'timestamp': msg.timestamp.strftime("%Y-%m-%d %I:%M %p")
                })
        
        return claims
    
    def build_finish_order(self, claims: List[Dict]) -> Tuple[List[str], Optional[str]]:
        """Build finish order from claims, return (order, ambiguity_note)"""
        
        # First check if we have a complete finish order
        for claim in claims:
            if claim['type'] == 'complete_finish_order':
                return claim['finish_order'], None
        
        # Build from relative positions
        boats = set()
        edges = []  # (ahead_boat, behind_boat) pairs
        
        for claim in claims:
            if claim['type'] == 'relative_position':
                ahead = claim['boat_ahead']
                behind = claim['boat_behind']
                boats.add(ahead)
                boats.add(behind)
                edges.append((ahead, behind))
        
        if not boats:
            return [], "No finish order data found"
        
        # Simple topological sort to determine order
        try:
            finish_order = self._topological_sort(boats, edges)
            return finish_order, None
        except Exception as e:
            return list(boats), f"Ambiguous finish order: {str(e)}"
    
    def _topological_sort(self, boats: Set[str], edges: List[Tuple[str, str]]) -> List[str]:
        """Perform topological sort on the boat positions"""
        from collections import defaultdict, deque
        
        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all boats with 0 in-degree
        for boat in boats:
            in_degree[boat] = 0
        
        # Build graph
        for ahead, behind in edges:
            graph[ahead].append(behind)
            in_degree[behind] += 1
        
        # Find boats with no incoming edges (should finish first)
        queue = deque([boat for boat in boats if in_degree[boat] == 0])
        result = []
        
        while queue:
            boat = queue.popleft()
            result.append(boat)
            
            # Remove this boat and update in-degrees
            for neighbor in graph[boat]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(boats):
            raise Exception("Circular dependency in finish order")
        
        return result
    
    def is_valid_boat_name(self, boat_name: str) -> bool:
        """Check if a boat name is valid (not a parsing artifact)"""
        boat_lower = boat_name.lower()
        
        # Filter out obvious non-boat names
        invalid_patterns = [
            r'^-\s',  # Starts with dash
            r'^\d+$',  # Just numbers
            r'ahead|behind',  # Contains position words
            r'not sure|no one|finished|jeromy',  # Non-boat phrases
            r'club boat|team\s|1nv',  # Generic terms
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, boat_lower):
                return False
        
        # Must have at least one letter
        if not re.search(r'[a-zA-Z]', boat_name):
            return False
        
        return True
    def calculate_scores(self, finish_order: List[str], claims: List[Dict]) -> Dict[str, Dict]:
        """Calculate scores for boats based on finish order and novice credits"""
        results = {}
        
        # Filter finish order to only include valid boat names
        valid_finish_order = [boat for boat in finish_order if self.is_valid_boat_name(boat)]
        
        # Get novice counts
        novice_counts = {}
        for claim in claims:
            if claim['type'] == 'novice' and self.is_valid_boat_name(claim['boat']):
                novice_counts[claim['boat']] = claim['count']
        
        # Get penalties
        penalties = {}
        for claim in claims:
            if claim['type'] == 'penalty' and self.is_valid_boat_name(claim['boat']):
                penalties[claim['boat']] = claim['penalty_type']
        
        starters_count = len(valid_finish_order)
        
        for i, boat in enumerate(valid_finish_order):
            position = i + 1
            novices = novice_counts.get(boat, 0)
            status = penalties.get(boat, 'FIN')
            
            # Calculate score based on rules
            if status in ['DSQ', 'DNF']:
                score = starters_count + 1
            else:
                # Normal score with novice credit: max(1, finish_position - min(2, novice_count))
                score = max(1, position - min(2, novices))
            
            results[boat] = {
                'boat': boat,
                'pos': position,
                'novices': novices,
                'status': status,
                'score': score,
                'aliasesUsed': []  # Would be populated if we tracked this
            }
        
        return results
    
    def process_weekly_race(self, date: str, messages: List[Message]) -> Dict:
        """Process a single week's race"""
        claims = self.extract_individual_claims(messages)
        finish_order, ambiguity = self.build_finish_order(claims)
        
        if not finish_order:
            return {
                'date': date,
                'starters': [],
                'results': [],
                'evidence': claims,
                'ambiguity': ambiguity or "No race data found"
            }
        
        boat_results = self.calculate_scores(finish_order, claims)
        results_list = [boat_results[boat] for boat in finish_order if boat in boat_results]
        valid_starters = [boat for boat in finish_order if self.is_valid_boat_name(boat)]
        
        return {
            'date': date,
            'starters': valid_starters,
            'results': results_list,
            'evidence': claims,
            'ambiguity': ambiguity
        }
    
    def generate_results(self) -> Dict:
        """Generate the complete results JSON"""
        self.parse_chat_file()
        
        # Process each Wednesday race
        boats_with_results = set()
        for date in sorted(self.weekly_races.keys()):
            week_data = self.process_weekly_race(date, self.weekly_races[date])
            if week_data['results']:  # Only include weeks with actual race results
                self.series_data['weeks'].append(week_data)
                # Only track boats that actually raced
                for result in week_data['results']:
                    boats_with_results.add(result['boat'])
        
        # Only include boats that actually participated in races
        self.series_data['boats_seen'] = sorted(list(boats_with_results))
        
        return {"series": self.series_data}

def main():
    if len(sys.argv) > 1:
        chat_file = sys.argv[1]
    else:
        chat_file = '_chat.txt'
    
    parser = EnhancedChatParser(chat_file)
    results = parser.generate_results()
    
    # Write results to JSON file
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Results written to results.json")
    print(f"Found {len(results['series']['weeks'])} race weeks with results")
    print(f"Boats seen: {results['series']['boats_seen']}")
    
    # Print summary of each week
    for week in results['series']['weeks']:
        print(f"\n{week['date']}: {len(week['results'])} boats")
        if week['ambiguity']:
            print(f"  Note: {week['ambiguity']}")

if __name__ == "__main__":
    main()