# test_velopark_parser.py
import unittest
from datetime import datetime
import re

# Copy the parsing functions from the main script for testing
def parse_week_date(week_title):
    """Parse week title like 'Week beginning 26 May' into a date"""
    match = re.search(r'Week beginning (\d+) (\w+)', week_title, re.IGNORECASE)
    if not match:
        return None
    
    day = int(match.group(1))
    month_name = match.group(2).lower()
    
    # Use 2025 as the year for current context
    year = 2025
    
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    month = months.get(month_name)
    if not month:
        return None
    
    try:
        return datetime(year, month, day)
    except ValueError:
        return None

def parse_time_slots(times_str):
    """Parse time strings like '07:00-21:00' or '07:00-14:00 16:00-21:00'"""
    if 'closed' in times_str.lower():
        return []
    
    # Remove content inside parentheses first (these are notes, not actual session times)
    # This prevents times like "(16:30-17:30 Abercrombie loop only)" from being parsed as sessions
    cleaned_str = re.sub(r'\([^)]*\)', '', times_str)
    
    # Normalize the string - replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', cleaned_str.strip())
    
    # Handle cases where times might be stuck together (e.g., "14:0016:00")
    # Insert space before a time that follows another time
    normalized = re.sub(r'(\d{2}:\d{2})(\d{2}:\d{2})', r'\1 \2', normalized)
    
    # Find all time ranges in format HH:MM-HH:MM with optional spaces around dash
    time_ranges = re.findall(r'\d{2}:\d{2}\s*-\s*\d{2}:\d{2}', normalized)
    
    slots = []
    for time_range in time_ranges:
        # Remove all spaces and split on dash
        clean_range = re.sub(r'\s', '', time_range)
        if '-' in clean_range:
            start_time, end_time = clean_range.split('-', 1)
            
            # Validate time format (exactly HH:MM)
            if (re.match(r'^\d{2}:\d{2}$', start_time) and 
                re.match(r'^\d{2}:\d{2}$', end_time)):
                slots.append((start_time, end_time))
    
    return slots

def extract_special_notes(times_str):
    """Extract special notes like '(Bank Holiday)' or '(Abercrombie loop only)'"""
    notes = re.findall(r'\([^)]+\)', times_str)
    return ' '.join(notes) if notes else ''

class TestVeloParkParser(unittest.TestCase):
    
    def setUp(self):
        """Test data from the actual VeloPark website"""
        self.test_schedule_data = {
            "Week beginning 26 May": {
                "Monday": "09:00-16:00 (Bank Holiday)",
                "Tuesday": "07:00-21:00",
                "Wednesday": "07:00-19:00",
                "Thursday": "07:00-21:00 (10:00-17:00 Abercrombie loop only)",
                "Friday": "07:00-14:00 16:00-21:00 (16:30-17:30 Abercrombie loop only)",
                "Saturday": "14:00-18:00",
                "Sunday": "Closed"
            },
            "Week beginning 2 June": {
                "Monday": "07:00-21:00",
                "Tuesday": "07:00-18:30",
                "Wednesday": "07:00-19:00",
                "Thursday": "07:00-21:00",
                "Friday": "07:00-21:00",
                "Saturday": "07:30-18:00",
                "Sunday": "14:00-18:00"
            },
            "Week beginning 9 June": {
                "Monday": "07:00-21:00",
                "Tuesday": "07:00-18:00",
                "Wednesday": "07:00-19:00",
                "Thursday": "07:00-21:00",
                "Friday": "07:00-21:00",
                "Saturday": "07:30-10:00 16:00-18:00",
                "Sunday": "07:30-18:00"
            }
        }

    def test_parse_week_date(self):
        """Test week date parsing"""
        # Test normal dates
        date = parse_week_date("Week beginning 26 May")
        self.assertEqual(date.day, 26)
        self.assertEqual(date.month, 5)
        
        date = parse_week_date("Week beginning 2 June")
        self.assertEqual(date.day, 2)
        self.assertEqual(date.month, 6)
        
        # Test invalid input
        self.assertIsNone(parse_week_date("Invalid format"))

    def test_parse_time_slots_single_session(self):
        """Test parsing single time sessions"""
        # Single session
        slots = parse_time_slots("07:00-21:00")
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0], ("07:00", "21:00"))
        
        # Single session with spaces
        slots = parse_time_slots("07:00 - 21:00")
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0], ("07:00", "21:00"))

    def test_parse_time_slots_multiple_sessions(self):
        """Test parsing multiple time sessions"""
        # Multiple sessions - this is the key test for Friday issue
        slots = parse_time_slots("07:00-14:00 16:00-21:00 (16:30-17:30 Abercrombie loop only)")
        print(f"Friday slots parsed: {slots}")  # Debug output
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0], ("07:00", "14:00"))
        self.assertEqual(slots[1], ("16:00", "21:00"))
        
        # Saturday with gap
        slots = parse_time_slots("07:30-10:00 16:00-18:00")
        print(f"Saturday slots parsed: {slots}")  # Debug output
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0], ("07:30", "10:00"))
        self.assertEqual(slots[1], ("16:00", "18:00"))

    def test_parse_time_slots_with_notes(self):
        """Test parsing with special notes"""
        # With bank holiday
        slots = parse_time_slots("09:00-16:00 (Bank Holiday)")
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0], ("09:00", "16:00"))
        
        # With complex notes that contain times - should ignore the time in parentheses
        slots = parse_time_slots("07:00-21:00 (10:00-17:00 Abercrombie loop only)")
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0], ("07:00", "21:00"))

    def test_parse_time_slots_closed(self):
        """Test parsing closed days"""
        slots = parse_time_slots("Closed")
        self.assertEqual(len(slots), 0)

    def test_extract_special_notes(self):
        """Test extracting special notes"""
        notes = extract_special_notes("09:00-16:00 (Bank Holiday)")
        self.assertEqual(notes, "(Bank Holiday)")
        
        notes = extract_special_notes("07:00-14:00 16:00-21:00 (16:30-17:30 Abercrombie loop only)")
        self.assertEqual(notes, "(16:30-17:30 Abercrombie loop only)")
        
        notes = extract_special_notes("07:00-21:00")
        self.assertEqual(notes, "")

    def test_real_data_friday_issue(self):
        """Test the specific Friday issue: should have 2 sessions"""
        friday_times = "07:00-14:00 16:00-21:00 (16:30-17:30 Abercrombie loop only)"
        slots = parse_time_slots(friday_times)
        
        print(f"\nFriday test:")
        print(f"Input: {friday_times}")
        print(f"Parsed slots: {slots}")
        print(f"Expected: [('07:00', '14:00'), ('16:00', '21:00')]")
        
        self.assertEqual(len(slots), 2, f"Friday should have 2 sessions, got {len(slots)}")
        self.assertIn(("07:00", "14:00"), slots, "Missing morning session 07:00-14:00")
        self.assertIn(("16:00", "21:00"), slots, "Missing afternoon session 16:00-21:00")

    def test_real_data_monday_issue(self):
        """Test the specific Monday issue: should have 1 session"""
        monday_times = "07:00-21:00"
        slots = parse_time_slots(monday_times)
        
        print(f"\nMonday test:")
        print(f"Input: {monday_times}")
        print(f"Parsed slots: {slots}")
        print(f"Expected: [('07:00', '21:00')]")
        
        self.assertEqual(len(slots), 1, f"Monday should have 1 session, got {len(slots)}")
        self.assertEqual(slots[0], ("07:00", "21:00"), "Monday session should be 07:00-21:00")

    def test_all_real_schedule_data(self):
        """Test parsing all the real schedule data"""
        print(f"\n{'='*60}")
        print("TESTING ALL REAL SCHEDULE DATA")
        print(f"{'='*60}")
        
        for week_title, week_data in self.test_schedule_data.items():
            print(f"\n{week_title}:")
            week_date = parse_week_date(week_title)
            print(f"  Week starts: {week_date}")
            
            for day, times in week_data.items():
                slots = parse_time_slots(times)
                notes = extract_special_notes(times)
                
                print(f"  {day:10} | {times:50} | Slots: {len(slots)} | {slots}")
                if notes:
                    print(f"             | Notes: {notes}")

    def test_edge_cases(self):
        """Test edge cases and potential issues"""
        # Test malformed times
        slots = parse_time_slots("07:00-14:0016:00-21:00")  # Missing space
        print(f"Malformed (no space): {slots}")
        self.assertEqual(len(slots), 2)  # Should still parse both
        
        # Test with extra spaces
        slots = parse_time_slots("07:00 - 14:00   16:00 - 21:00")
        print(f"Extra spaces: {slots}")
        self.assertEqual(len(slots), 2)
        
        # Test with different note formats
        slots = parse_time_slots("07:00-21:00(Note without space)")
        print(f"Note without space: {slots}")
        self.assertEqual(len(slots), 1)

if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)