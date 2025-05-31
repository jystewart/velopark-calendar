# test_actual_calendar.py
import unittest
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from api/
# Since we're in tests/ folder, we need to go up one level to reach project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the actual functions from the Vercel API
try:
    from api.calendar import (
        parse_time_slots,
        parse_week_date,
        extract_special_notes,
        generate_icalendar,
        scrape_velopark_schedule
    )
    print("✓ Successfully imported functions from api/calendar.py")
except ImportError as e:
    print(f"✗ Failed to import from api/calendar.py: {e}")
    print("Make sure you're running this from the tests directory")
    print("Project structure should be:")
    print("  your-project/")
    print("  ├── api/")
    print("  │   └── calendar.py")
    print("  └── tests/")
    print("      ├── test_actual_calendar.py")
    print("      └── quick_test.py")
    print("\nRun from tests directory:")
    print("  cd your-project/tests")
    print("  python test_actual_calendar.py")
    sys.exit(1)

class TestActualCalendarFunctions(unittest.TestCase):
    
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

    def test_parse_time_slots_friday_issue(self):
        """Test the specific Friday issue using actual function"""
        friday_times = "07:00-14:00 16:00-21:00 (16:30-17:30 Abercrombie loop only)"
        slots = parse_time_slots(friday_times)
        
        print(f"\n=== FRIDAY TEST (using actual function) ===")
        print(f"Input: {friday_times}")
        print(f"Parsed slots: {slots}")
        print(f"Expected: [('07:00', '14:00'), ('16:00', '21:00')]")
        
        self.assertEqual(len(slots), 2, f"Friday should have 2 sessions, got {len(slots)}")
        self.assertIn(("07:00", "14:00"), slots, "Missing morning session 07:00-14:00")
        self.assertIn(("16:00", "21:00"), slots, "Missing afternoon session 16:00-21:00")

    def test_parse_time_slots_monday_issue(self):
        """Test the specific Monday issue using actual function"""
        monday_times = "07:00-21:00"
        slots = parse_time_slots(monday_times)
        
        print(f"\n=== MONDAY TEST (using actual function) ===")
        print(f"Input: {monday_times}")
        print(f"Parsed slots: {slots}")
        print(f"Expected: [('07:00', '21:00')]")
        
        self.assertEqual(len(slots), 1, f"Monday should have 1 session, got {len(slots)}")
        self.assertEqual(slots[0], ("07:00", "21:00"), "Monday session should be 07:00-21:00")

    def test_parse_time_slots_with_notes(self):
        """Test that times in notes are ignored"""
        test_cases = [
            {
                "input": "09:00-16:00 (Bank Holiday)",
                "expected_slots": 1,
                "description": "Bank holiday"
            },
            {
                "input": "07:00-21:00 (10:00-17:00 Abercrombie loop only)",
                "expected_slots": 1,
                "description": "Note with time range should be ignored"
            },
            {
                "input": "07:30-10:00 16:00-18:00",
                "expected_slots": 2,
                "description": "Saturday with gap"
            }
        ]
        
        print(f"\n=== NOTES TEST (using actual function) ===")
        for test_case in test_cases:
            with self.subTest(test_case["description"]):
                slots = parse_time_slots(test_case["input"])
                print(f"{test_case['description']:30} | {test_case['input']:50} | Got {len(slots)} slots")
                self.assertEqual(len(slots), test_case["expected_slots"])

    def test_parse_week_date_actual(self):
        """Test week date parsing using actual function"""
        print(f"\n=== WEEK DATE TEST (using actual function) ===")
        
        test_weeks = [
            ("Week beginning 26 May", 26, 5),
            ("Week beginning 2 June", 2, 6),
            ("Week beginning 9 June", 9, 6)
        ]
        
        for week_title, expected_day, expected_month in test_weeks:
            with self.subTest(week_title):
                date = parse_week_date(week_title)
                self.assertIsNotNone(date, f"Failed to parse: {week_title}")
                self.assertEqual(date.day, expected_day)
                self.assertEqual(date.month, expected_month)
                print(f"{week_title:25} → {date} ({date.strftime('%A')})")

    def test_extract_special_notes_actual(self):
        """Test special notes extraction using actual function"""
        print(f"\n=== SPECIAL NOTES TEST (using actual function) ===")
        
        test_cases = [
            ("09:00-16:00 (Bank Holiday)", "(Bank Holiday)"),
            ("07:00-14:00 16:00-21:00 (16:30-17:30 Abercrombie loop only)", "(16:30-17:30 Abercrombie loop only)"),
            ("07:00-21:00", ""),
        ]
        
        for input_str, expected_notes in test_cases:
            with self.subTest(input_str):
                notes = extract_special_notes(input_str)
                print(f"Input: {input_str:50} → Notes: {notes}")
                self.assertEqual(notes, expected_notes)

    def test_full_schedule_parsing(self):
        """Test parsing the entire schedule using actual functions"""
        print(f"\n=== FULL SCHEDULE TEST (using actual functions) ===")
        
        total_events = 0
        issues = []
        
        for week_title, week_data in self.test_schedule_data.items():
            week_date = parse_week_date(week_title)
            print(f"\n{week_title} (starts {week_date.strftime('%A %d %B %Y') if week_date else 'PARSE ERROR'}):")
            
            if not week_date:
                issues.append(f"Could not parse week: {week_title}")
                continue
            
            for day_name, times_str in week_data.items():
                slots = parse_time_slots(times_str)
                notes = extract_special_notes(times_str)
                
                total_events += len(slots)
                
                print(f"  {day_name:10}: {times_str:45} → {len(slots)} events {slots}")
                if notes:
                    print(f"             Notes: {notes}")
                
                # Check for specific known issues
                if day_name == "Friday" and "16:30-17:30" in times_str and len(slots) != 2:
                    issues.append(f"Friday issue: expected 2 slots, got {len(slots)} for '{times_str}'")
                
                if day_name == "Monday" and times_str == "07:00-21:00" and len(slots) != 1:
                    issues.append(f"Monday issue: expected 1 slot, got {len(slots)} for '{times_str}'")
        
        print(f"\n=== SUMMARY ===")
        print(f"Total events that would be generated: {total_events}")
        print(f"Issues found: {len(issues)}")
        
        for issue in issues:
            print(f"  ⚠️  {issue}")
        
        # Assert no critical issues
        self.assertEqual(len(issues), 0, f"Found {len(issues)} parsing issues")

    def test_icalendar_generation(self):
        """Test that iCalendar generation works with actual functions"""
        print(f"\n=== ICALENDAR GENERATION TEST ===")
        
        try:
            ics_content = generate_icalendar(
                self.test_schedule_data, 
                "Test Calendar", 
                include_notes=True, 
                weeks_ahead=4
            )
            
            # Basic validation
            self.assertIn("BEGIN:VCALENDAR", ics_content)
            self.assertIn("END:VCALENDAR", ics_content)
            self.assertIn("BEGIN:VEVENT", ics_content)
            self.assertIn("END:VEVENT", ics_content)
            
            # Count events
            event_count = ics_content.count("BEGIN:VEVENT")
            print(f"Generated iCalendar with {event_count} events")
            print(f"Calendar length: {len(ics_content)} characters")
            
            # Validate some content
            self.assertIn("Lee Valley VeloPark", ics_content)
            self.assertIn("DTSTART:", ics_content)
            self.assertIn("DTEND:", ics_content)
            
            print("✓ iCalendar generation successful")
            
        except Exception as e:
            self.fail(f"iCalendar generation failed: {e}")

    def test_live_website_scraping(self):
        """Test scraping the actual website (optional - may be slow)"""
        print(f"\n=== LIVE WEBSITE SCRAPING TEST ===")
        print("This test scrapes the actual VeloPark website...")
        
        try:
            # This will make a real HTTP request
            live_schedule = scrape_velopark_schedule()
            
            self.assertIsInstance(live_schedule, dict)
            self.assertGreater(len(live_schedule), 0, "No schedule data found on website")
            
            print(f"✓ Successfully scraped {len(live_schedule)} weeks of data from live website")
            
            # Show what we got
            for week_title, week_data in live_schedule.items():
                print(f"  {week_title}: {len(week_data)} days")
            
        except Exception as e:
            print(f"⚠️  Live scraping failed (this may be normal): {e}")
            # Don't fail the test for this - the website might be down or blocking requests

if __name__ == "__main__":
    print("Testing actual functions from api/calendar.py")
    print("=" * 60)
    unittest.main(verbosity=2)