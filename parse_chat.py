#!/usr/bin/env python3
"""
Enhanced PPYC Wednesday Night Racing Chat Parser

Parses WhatsApp chat export to generate race results in JSON format.
Follows specifications in .github/instructions/chat-instructions.md
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set, Iterable
from collections import defaultdict, namedtuple, deque
import os
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
        self._weekly_boats_seen: Set[str] = set()  # cumulative unique boats (for DNC scoring)
        
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
            # Expanded novice patterns:  "2 novices", "2 nv", "(2 novices)" "4nv"
            novice_pattern = r'(\d+)\s*(?:novice|novices|nv|nvs)\b'
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
        """Perform topological sort on the boat positions.
        If multiple valid orders exist, one valid order is returned; ranges will later
        capture ambiguity."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        for b in boats:
            in_degree[b] = 0
        for a, b in edges:
            graph[a].append(b)
            in_degree[b] += 1
        queue = deque(sorted([b for b in boats if in_degree[b] == 0]))  # deterministic
        order = []
        while queue:
            b = queue.popleft()
            order.append(b)
            for n in graph[b]:
                in_degree[n] -= 1
                if in_degree[n] == 0:
                    queue.append(n)
        if len(order) != len(boats):
            raise Exception("Circular dependency in finish order")
        return order

    def _compute_position_ranges(self, boats: Iterable[str], edges: List[Tuple[str, str]]) -> Dict[str, Tuple[int, int]]:
        """Given a (possibly) partially ordered set of boats (edges a->b means a ahead b),
        compute possible position range [min,max] for each boat (1-indexed)."""
        boats = list(boats)
        n = len(boats)
        graph_fwd = defaultdict(set)
        graph_rev = defaultdict(set)
        for a, b in edges:
            graph_fwd[a].add(b)
            graph_rev[b].add(a)

        def ancestors(b: str) -> Set[str]:
            seen = set()
            stack = [b]
            while stack:
                cur = stack.pop()
                for p in graph_rev[cur]:
                    if p not in seen:
                        seen.add(p)
                        stack.append(p)
            return seen

        def descendants(b: str) -> Set[str]:
            seen = set()
            stack = [b]
            while stack:
                cur = stack.pop()
                for c in graph_fwd[cur]:
                    if c not in seen:
                        seen.add(c)
                        stack.append(c)
            return seen

        ranges = {}
        for b in boats:
            anc = ancestors(b)
            desc = descendants(b)
            min_pos = len(anc) + 1
            max_pos = n - len(desc)
            ranges[b] = (min_pos, max_pos)
        return ranges
    
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

    def _apply_dnc(self, week_results: Dict, cumulative_boats: Set[str]):
        """Add DNC entries for boats that previously raced but are absent this week.
        DNC score = unique boats that have raced in series up to this point + 1."""
        starters = set(week_results.get('starters', []))
        prior_series_boats = set(cumulative_boats)  # copy
        dnc_boats = prior_series_boats - starters
        if not dnc_boats:
            return
        series_boats_after = prior_series_boats | starters
        dnc_score = len(series_boats_after) + 1

        # Ensure a concrete 'results' list exists (merge provisional if necessary)
        if 'results' not in week_results:
            # Convert provisional to definitive list for augmentation (retain provisional copy)
            provisional = week_results.get('results_provisional', [])
            week_results['results'] = [dict(r) for r in provisional]

        for boat in sorted(dnc_boats):
            week_results['results'].append({
                'boat': boat,
                'pos': None,
                'novices': 0,
                'status': 'DNC',
                'score': dnc_score,
                'aliasesUsed': []
            })
        week_results['results'].sort(key=lambda r: (r['pos'] is None, r['pos'] if r['pos'] is not None else 999, r['boat']))
    
    def process_weekly_race(self, date: str, messages: List[Message]) -> Dict:
        """Process a single week's race including ambiguity ranges and DNC.

        Returns week dict with either definitive 'results' or 'results_provisional' if ambiguous.
        """
        claims = self.extract_individual_claims(messages)
        finish_order, ambiguity = self.build_finish_order(claims)

        if not finish_order:
            return {
                'date': date,
                'starters': [],
                'results': [],
                'evidence': claims,
                'ambiguity': ambiguity or "No race data found",
                'status': 'NO_RACE'
            }

        # Build relative graph edges for ranges
        edges = []
        for c in claims:
            if c.get('type') == 'relative_position':
                edges.append((c['boat_ahead'], c['boat_behind']))

        # Compute ranges (even if unambiguous, helpful for transparency)
        ranges = self._compute_position_ranges(finish_order, edges)

        boat_results = self.calculate_scores(finish_order, claims)
        valid_starters = [b for b in finish_order if self.is_valid_boat_name(b)]

        # If ambiguity note present (cycle or partial), store provisional with ranges
        if ambiguity:
            provisional = []
            for b in finish_order:
                if b not in boat_results:  # skip invalid
                    continue
                min_p, max_p = ranges[b]
                # Representative pos used in scoring = current (topological) index +1
                representative_pos = boat_results[b]['pos']
                provisional.append({
                    'boat': b,
                    'pos': representative_pos,
                    'range': f"{min_p}-{max_p}",
                    'novices': boat_results[b]['novices'],
                    'status': boat_results[b]['status'],
                    'score': boat_results[b]['score']
                })
            week = {
                'date': date,
                'starters': valid_starters,
                'results_provisional': provisional,
                'evidence': claims,
                'ambiguity': {
                    'description': ambiguity,
                    'ranges': {b: {'min': ranges[b][0], 'max': ranges[b][1]} for b in finish_order}
                },
                'status': 'AMBIGUOUS'
            }
        else:
            results_list = []
            for b in finish_order:
                if b not in boat_results:
                    continue
                min_p, max_p = ranges[b]
                r = boat_results[b].copy()
                r['range'] = f"{min_p}-{max_p}"  # identical bounds if unambiguous
                results_list.append(r)
            week = {
                'date': date,
                'starters': valid_starters,
                'results': results_list,
                'evidence': claims,
                'ambiguity': None,
                'status': 'OK'
            }

        # Track cumulative boats for DNC scoring later (only if there were starters)
        if valid_starters:
            self._weekly_boats_seen |= set(valid_starters)

        return week
    
    def generate_results(self) -> Dict:
        """Generate the complete results JSON"""
        self.parse_chat_file()
        
        # Process each Wednesday race
        boats_with_results = set()
        weeks = []
        cumulative_series_boats: Set[str] = set()
        for date in sorted(self.weekly_races.keys()):
            week_data = self.process_weekly_race(date, self.weekly_races[date])
            # Determine if we treat as a scored race (starters > 0 and have some result info)
            has_results = bool(week_data.get('results')) or bool(week_data.get('results_provisional'))
            if has_results and week_data.get('starters'):
                # Apply DNC scoring BEFORE adding this week's starters to cumulative set for next week
                self._apply_dnc(week_data if 'results' in week_data else week_data, cumulative_series_boats)
                cumulative_series_boats |= set(week_data['starters'])
                weeks.append(week_data)
                for section in ['results', 'results_provisional']:
                    if section in week_data:
                        for result in week_data[section]:
                            if result.get('status') not in ('DNC',) and result.get('boat'):
                                boats_with_results.add(result['boat'])

        self.series_data['weeks'] = weeks
        self.series_data['boats_seen'] = sorted(list(boats_with_results))

        # Compute standings
        self._compute_standings()
        return {"series": self.series_data}

    def _compute_standings(self):
        """Compute series standings with throwouts (1 worst per 4 races)."""
        # Collect scores per boat
        boat_scores: Dict[str, List[int]] = defaultdict(list)
        race_count = 0
        for w in self.series_data['weeks']:
            # Only count races with starters
            if not w.get('starters'):
                continue
            race_count += 1
            # Choose appropriate results key
            key = 'results' if 'results' in w else 'results_provisional'
            for r in w[key]:
                if r['status'] == 'DNC':
                    boat_scores[r['boat']].append(r['score'])
                elif r.get('pos') is not None:
                    boat_scores[r['boat']].append(r['score'])

        throwouts = race_count // 4
        standings = []
        for boat, scores in boat_scores.items():
            sorted_scores = sorted(scores, reverse=True)  # worst first
            dropped = sorted_scores[:throwouts]
            kept = sorted_scores[throwouts:]
            standings.append({
                'boat': boat,
                'races': len(scores),
                'raw_total': sum(scores),
                'dropped': dropped,
                'net': sum(kept)
            })
        standings.sort(key=lambda x: (x['net'], x['raw_total']))
        self.series_data['standings'] = standings

    # ------------------------------ Output Helpers ------------------------------
    def write_week_files(self):
        """Emit per-week JSON and Markdown files in results/ directory."""
        os.makedirs('results', exist_ok=True)
        for w in self.series_data['weeks']:
            date = w['date']
            json_path = os.path.join('results', f"{date}.auto.json")
            md_path = os.path.join('results', f"{date}.auto.md")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(w, f, indent=2, ensure_ascii=False)
            # Markdown table
            lines = [f"# {date} Results (Auto Parsed)", ""]
            if w.get('ambiguity'):
                lines.append(f"Ambiguity: {w['ambiguity']['description'] if isinstance(w['ambiguity'], dict) else w['ambiguity']}")
                lines.append("")
            header = "| Pos | Boat | Range | Novices | Status | Score |"
            lines += [header, "|---:|---|---|---:|---|---:|"]
            key = 'results' if 'results' in w else 'results_provisional'
            for r in w[key]:
                pos_display = r['pos'] if r.get('pos') is not None else ''
                rng = r.get('range', '') if 'range' in r else r.get('range', '')
                lines.append(f"| {pos_display} | {r['boat']} | {rng} | {r.get('novices',0)} | {r.get('status','FIN')} | {r.get('score','')} |")
            lines.append("")
            lines.append("## Evidence")
            for ev in w.get('evidence', []):
                lines.append(f"- [{ev.get('timestamp','')}] {ev.get('author','')} — {ev.get('text','').replace('|','/')}" )
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))

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