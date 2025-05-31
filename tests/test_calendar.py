# test_calendar.py
import unittest
import sys
import os
import re
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from api/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the actual functions from the Vercel API
try:
    from api.calendar import (
        parse_time_slots, 
        parse_week_date, 
        extract_special_notes,
        generate_icalendar,
        generate_debug_info,
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
    print("      └── test_calendar.py")
    print("\nRun from tests directory:")
    print("  cd your-project/tests")
    print("  python test_calendar.py")
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
        
        current_year = datetime.now().year
        
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
                self.assertEqual(date.year, current_year, f"Year should be current year ({current_year})")
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

    def test_no_events_beyond_available_data(self):
        """Test that no events are generated beyond the available schedule data"""
        print(f"\n=== NO EVENTS BEYOND AVAILABLE DATA TEST ===")
        
        # Generate calendar with the actual schedule data
        ics_content = generate_icalendar(
            self.test_schedule_data, 
            "Test Calendar", 
            include_notes=True, 
            weeks_ahead=12  # Request 12 weeks but we only have 3 weeks of data
        )
        
        # Extract all DTSTART dates from the calendar
        dtstart_matches = re.findall(r'DTSTART:(\d{8})', ics_content)
        event_dates = []
        
        for date_str in dtstart_matches:
            # Parse YYYYMMDD format
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            event_date = datetime(year, month, day)
            event_dates.append(event_date)
        
        if event_dates:
            earliest_date = min(event_dates)
            latest_date = max(event_dates)
            
            print(f"Earliest event: {earliest_date.strftime('%A %d %B %Y')}")
            print(f"Latest event: {latest_date.strftime('%A %d %B %Y')}")
            print(f"Total events: {len(event_dates)}")
            
            # The latest event should not be beyond June 15 of current year (end of "Week beginning 9 June")
            current_year = datetime.now().year
            expected_last_date = datetime(current_year, 6, 15)  # Sunday of week beginning June 9
            
            self.assertLessEqual(latest_date, expected_last_date, 
                f"Events found beyond available data! Latest event: {latest_date}, Expected max: {expected_last_date}")
            
            # Check that we have events in the expected range
            expected_first_date = datetime(current_year, 5, 26)  # Monday of week beginning May 26
            self.assertGreaterEqual(earliest_date, expected_first_date,
                f"Events found before expected start! Earliest event: {earliest_date}, Expected min: {expected_first_date}")
            
            print(f"✓ All events are within the expected date range")
            print(f"  From: {expected_first_date.strftime('%A %d %B %Y')}")
            print(f"  To: {expected_last_date.strftime('%A %d %B %Y')}")
            
        else:
            self.fail("No events were generated from the test data")

    def test_specific_date_boundaries(self):
        """Test specific date boundaries to ensure no events leak beyond available data"""
        print(f"\n=== SPECIFIC DATE BOUNDARIES TEST ===")
        
        # Generate calendar events
        ics_content = generate_icalendar(
            self.test_schedule_data, 
            "Test Calendar", 
            include_notes=True, 
            weeks_ahead=20  # Request many weeks to test boundary
        )
        
        # Find all event dates
        dtstart_matches = re.findall(r'DTSTART:(\d{8})', ics_content)
        
        current_year = datetime.now().year
        prohibited_dates = [
            datetime(current_year, 6, 16),  # Monday after last week
            datetime(current_year, 6, 17),  # Tuesday after last week
            datetime(current_year, 6, 22),  # The following week
            datetime(current_year, 7, 1),   # July (definitely beyond data)
        ]
        
        events_beyond_data = []
        
        for date_str in dtstart_matches:
            year = int(date_str[:4])
            month = int(date_str[4:6]) 
            day = int(date_str[6:8])
            event_date = datetime(year, month, day)
            
            for prohibited_date in prohibited_dates:
                if event_date >= prohibited_date:
                    events_beyond_data.append(event_date)
        
        print(f"Checking for events on or after prohibited dates:")
        for date in prohibited_dates:
            print(f"  - {date.strftime('%A %d %B %Y')}")
        
        if events_beyond_data:
            print(f"✗ Found {len(events_beyond_data)} events beyond available data:")
            for bad_date in events_beyond_data[:5]:  # Show first 5
                print(f"    - {bad_date.strftime('%A %d %B %Y')}")
            self.fail(f"Found {len(events_beyond_data)} events beyond available schedule data")
        else:
            print(f"✓ No events found beyond available data")

    def test_week_coverage_completeness(self):
        """Test that we have complete coverage for the weeks we do have data for"""
        print(f"\n=== WEEK COVERAGE COMPLETENESS TEST ===")
        
        # Generate calendar
        ics_content = generate_icalendar(
            self.test_schedule_data, 
            "Test Calendar", 
            include_notes=True, 
            weeks_ahead=8
        )
        
        # Expected weeks and their date ranges (using current year)
        current_year = datetime.now().year
        expected_weeks = [
            ("Week beginning 26 May", datetime(current_year, 5, 26), datetime(current_year, 6, 1)),
            ("Week beginning 2 June", datetime(current_year, 6, 2), datetime(current_year, 6, 8)),
            ("Week beginning 9 June", datetime(current_year, 6, 9), datetime(current_year, 6, 15)),
        ]
        
        # Extract event dates
        dtstart_matches = re.findall(r'DTSTART:(\d{8})', ics_content)
        event_dates = set()
        
        for date_str in dtstart_matches:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            event_date = datetime(year, month, day)
            event_dates.add(event_date)
        
        # Check each expected week
        for week_title, week_start, week_end in expected_weeks:
            print(f"\nChecking {week_title} ({week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}):")
            
            week_events = []
            current_date = week_start
            
            while current_date <= week_end:
                if current_date in event_dates:
                    week_events.append(current_date)
                current_date += timedelta(days=1)
            
            print(f"  Events found on {len(week_events)} days:")
            for event_date in week_events:
                day_name = event_date.strftime('%A')
                # Get the expected times for this day from test data
                expected_times = self.test_schedule_data[week_title].get(day_name, "Not found")
                print(f"    {event_date.strftime('%a %d %b')}: {expected_times}")
            
            # Verify we have events for non-closed days
            week_data = self.test_schedule_data[week_title]
            expected_event_days = sum(1 for times in week_data.values() if 'closed' not in times.lower())
            
            if len(week_events) > 0:
                print(f"  ✓ Week has {len(week_events)} event days (expected non-closed days: {expected_event_days})")
            else:
                print(f"  ✗ No events found for this week!")

    def test_no_pattern_repetition(self):
        """Test that patterns don't repeat beyond available data"""
        print(f"\n=== NO PATTERN REPETITION TEST ===")
        
        # Generate calendar with request for many weeks
        ics_content = generate_icalendar(
            self.test_schedule_data, 
            "Test Calendar", 
            include_notes=True, 
            weeks_ahead=15  # Request way more weeks than we have data for
        )
        
        # Look for events that would indicate pattern repetition
        # For example, if we see events on June 23 (which would be Monday of week 4), 
        # that suggests the pattern is repeating
        
        # Extract all event lines with dates
        event_lines = []
        for line in ics_content.split('\n'):
            if 'DTSTART:' in line:
                event_lines.append(line)
        
        # Convert to actual dates and check for suspicious patterns
        event_dates = []
        for line in event_lines:
            date_match = re.search(r'DTSTART:(\d{8})', line)
            if date_match:
                date_str = date_match.group(1)
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                event_dates.append(datetime(year, month, day))
        
        # Sort dates
        event_dates.sort()
        
        # Check for events that would indicate week 4 repetition (June 16-22)
        current_year = datetime.now().year
        week4_start = datetime(current_year, 6, 16)
        week4_end = datetime(current_year, 6, 22)
        
        # Check for events that would indicate week 5 repetition (June 23-29)
        week5_start = datetime(current_year, 6, 23)
        week5_end = datetime(current_year, 6, 29)
        
        repetition_events = []
        for event_date in event_dates:
            if (week4_start <= event_date <= week4_end) or (week5_start <= event_date <= week5_end):
                repetition_events.append(event_date)
        
        print(f"Total events generated: {len(event_dates)}")
        if event_dates:
            print(f"Date range: {event_dates[0].strftime('%d %b')} to {event_dates[-1].strftime('%d %b')}")
        
        print(f"Events that suggest pattern repetition: {len(repetition_events)}")
        
        if repetition_events:
            print("Suspicious events (suggesting pattern repetition):")
            for bad_date in repetition_events[:5]:
                print(f"  - {bad_date.strftime('%A %d %B %Y')}")
            self.fail(f"Found {len(repetition_events)} events that suggest pattern repetition beyond available data")
        else:
            print("✓ No pattern repetition detected")

    def test_year_boundary_edge_cases(self):
        """Test year boundary logic for December/January transitions"""
        print(f"\n=== YEAR BOUNDARY EDGE CASES TEST ===")
        
        # We need to test the logic by temporarily modifying what the function thinks is "now"
        # We'll monkey patch datetime.now() to simulate different current dates
        
        from unittest.mock import patch
        
        test_cases = [
            # Format: (current_date, week_title, expected_year, description)
            
            # December scenarios - January dates should be next year
            ("2024-12-15", "Week beginning 6 January", 2025, "December 2024 → January should be 2025"),
            ("2024-12-31", "Week beginning 1 January", 2025, "December 31 → January should be next year"),
            ("2024-12-01", "Week beginning 13 January", 2025, "Early December → January should be next year"),
            
            # January scenarios - December dates should be previous year
            ("2025-01-15", "Week beginning 30 December", 2024, "January 2025 → December should be 2024"),
            ("2025-01-01", "Week beginning 23 December", 2024, "January 1 → December should be previous year"),
            ("2025-01-31", "Week beginning 16 December", 2024, "Late January → December should be previous year"),
            
            # Normal cases within the same year
            ("2025-05-15", "Week beginning 26 May", 2025, "May → May should be same year"),
            ("2025-06-01", "Week beginning 2 June", 2025, "June → June should be same year"),
            ("2025-11-15", "Week beginning 3 November", 2025, "November → November should be same year"),
            
            # Edge cases - February scenarios (should not trigger cross-year logic)
            ("2025-02-15", "Week beginning 10 February", 2025, "February → February should be same year"),
            ("2025-02-28", "Week beginning 3 March", 2025, "Late February → March should be same year"),
            
            # Edge cases - November scenarios (should not trigger cross-year logic)
            ("2025-11-30", "Week beginning 1 December", 2025, "November → December should be same year"),
            ("2025-10-15", "Week beginning 3 November", 2025, "October → November should be same year"),
        ]
        
        for current_date_str, week_title, expected_year, description in test_cases:
            with self.subTest(description):
                # Parse the mock current date
                mock_current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
                
                # Mock datetime.now() to return our test date
                with patch('api.calendar.datetime') as mock_datetime:
                    mock_datetime.now.return_value = mock_current_date
                    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                    
                    # Test the actual function
                    result_date = parse_week_date(week_title)
                    
                    if result_date:
                        print(f"{description:50} | Current: {current_date_str} | Week: {week_title:25} | Got year: {result_date.year} | Expected: {expected_year}")
                        self.assertEqual(result_date.year, expected_year, 
                            f"Year mismatch for {description}. Current date: {current_date_str}, Week: {week_title}")
                    else:
                        self.fail(f"Failed to parse date for {description}: {week_title}")

    def test_year_boundary_specific_months(self):
        """Test specific month combinations that should trigger year adjustments"""
        print(f"\n=== SPECIFIC MONTH BOUNDARY TEST ===")
        
        from unittest.mock import patch
        
        # Test December → January (should increment year)
        december_to_january_cases = [
            ("2024-12-01", "Week beginning 1 January", 2025),
            ("2024-12-15", "Week beginning 8 January", 2025),
            ("2024-12-31", "Week beginning 15 January", 2025),
            ("2024-12-25", "Week beginning 22 January", 2025),
        ]
        
        print("Testing December → January transitions:")
        for current_date_str, week_title, expected_year in december_to_january_cases:
            mock_current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
            
            with patch('api.calendar.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_current_date
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                result_date = parse_week_date(week_title)
                self.assertIsNotNone(result_date, f"Failed to parse: {week_title}")
                self.assertEqual(result_date.year, expected_year)
                print(f"  ✓ {current_date_str} + {week_title} → {result_date.year}")
        
        # Test January → December (should decrement year)
        january_to_december_cases = [
            ("2025-01-01", "Week beginning 30 December", 2024),
            ("2025-01-15", "Week beginning 23 December", 2024),
            ("2025-01-31", "Week beginning 16 December", 2024),
            ("2025-01-10", "Week beginning 9 December", 2024),
        ]
        
        print("\nTesting January → December transitions:")
        for current_date_str, week_title, expected_year in january_to_december_cases:
            mock_current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
            
            with patch('api.calendar.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_current_date
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                result_date = parse_week_date(week_title)
                self.assertIsNotNone(result_date, f"Failed to parse: {week_title}")
                self.assertEqual(result_date.year, expected_year)
                print(f"  ✓ {current_date_str} + {week_title} → {result_date.year}")

    def test_year_boundary_no_false_positives(self):
        """Test that normal month transitions don't trigger year changes"""
        print(f"\n=== NO FALSE POSITIVES TEST ===")
        
        from unittest.mock import patch
        
        # These should NOT trigger year adjustments
        normal_cases = [
            ("2025-03-15", "Week beginning 10 March", 2025, "March → March"),
            ("2025-05-30", "Week beginning 2 June", 2025, "May → June"),
            ("2025-08-15", "Week beginning 18 August", 2025, "August → August"),
            ("2025-10-15", "Week beginning 3 November", 2025, "October → November"),
            ("2025-11-25", "Week beginning 1 December", 2025, "November → December"),
            ("2025-02-15", "Week beginning 3 March", 2025, "February → March"),
            ("2025-04-30", "Week beginning 5 May", 2025, "April → May"),
        ]
        
        for current_date_str, week_title, expected_year, description in normal_cases:
            with self.subTest(description):
                mock_current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
                
                with patch('api.calendar.datetime') as mock_datetime:
                    mock_datetime.now.return_value = mock_current_date
                    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                    
                    result_date = parse_week_date(week_title)
                    self.assertIsNotNone(result_date, f"Failed to parse: {week_title}")
                    self.assertEqual(result_date.year, expected_year)
                    print(f"  ✓ {description:20} | {current_date_str} + {week_title} → {result_date.year} (correct)")

    def test_year_boundary_edge_case_validation(self):
        """Test edge cases around the exact boundary dates"""
        print(f"\n=== YEAR BOUNDARY EDGE CASE VALIDATION ===")
        
        from unittest.mock import patch
        
        # Test various January dates in different contexts
        edge_cases = [
            # When it's January 1st, December dates should be previous year
            ("2025-01-01", "Week beginning 1 January", 2025, "New Year's Day → January same year"),
            ("2025-01-01", "Week beginning 31 December", 2024, "New Year's Day → December previous year"),
            
            # When it's December 31st, January dates should be next year  
            ("2024-12-31", "Week beginning 31 December", 2024, "New Year's Eve → December same year"),
            ("2024-12-31", "Week beginning 1 January", 2025, "New Year's Eve → January next year"),
            
            # Mid-month scenarios
            ("2025-01-15", "Week beginning 15 January", 2025, "Mid January → January same year"),
            ("2025-01-15", "Week beginning 15 December", 2024, "Mid January → December previous year"),
            ("2024-12-15", "Week beginning 15 December", 2024, "Mid December → December same year"),
            ("2024-12-15", "Week beginning 15 January", 2025, "Mid December → January next year"),
        ]
        
        for current_date_str, week_title, expected_year, description in edge_cases:
            with self.subTest(description):
                mock_current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
                
                with patch('api.calendar.datetime') as mock_datetime:
                    mock_datetime.now.return_value = mock_current_date
                    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                    
                    result_date = parse_week_date(week_title)
                    self.assertIsNotNone(result_date, f"Failed to parse: {week_title}")
                    self.assertEqual(result_date.year, expected_year, 
                        f"Wrong year for {description}. Expected {expected_year}, got {result_date.year}")
                    print(f"  ✓ {description}")

    def test_real_world_scenarios(self):
        """Test real-world scenarios that might occur"""
        print(f"\n=== REAL WORLD SCENARIOS TEST ===")
        
        from unittest.mock import patch
        
        # Realistic scenarios that could happen in practice
        real_scenarios = [
            # Gym publishes next week's schedule in December
            ("2024-12-20", "Week beginning 30 December", 2024, "Late December publishing current year schedule"),
            ("2024-12-27", "Week beginning 6 January", 2025, "Late December publishing new year schedule"),
            
            # Gym publishes schedule in early January for both years
            ("2025-01-03", "Week beginning 30 December", 2024, "Early January referencing previous year"),
            ("2025-01-03", "Week beginning 6 January", 2025, "Early January referencing current year"),
            
            # Normal operations throughout the year
            ("2025-05-15", "Week beginning 19 May", 2025, "Normal May operations"),
            ("2025-09-10", "Week beginning 15 September", 2025, "Normal September operations"),
        ]
        
        for current_date_str, week_title, expected_year, description in real_scenarios:
            with self.subTest(description):
                mock_current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
                
                with patch('api.calendar.datetime') as mock_datetime:
                    mock_datetime.now.return_value = mock_current_date
                    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                    
                    result_date = parse_week_date(week_title)
                    self.assertIsNotNone(result_date, f"Failed to parse: {week_title}")
                    self.assertEqual(result_date.year, expected_year)
                    print(f"  ✓ {description}")
                    print(f"    Current: {current_date_str}, Week: {week_title} → {result_date.strftime('%Y-%m-%d (%A)')}")

    def test_debug_info_boundaries(self):
        """Test that debug info correctly shows boundaries"""
        print(f"\n=== DEBUG INFO BOUNDARIES TEST ===")
        
        debug_info = generate_debug_info(self.test_schedule_data, weeks_ahead=10)
        
        # Check that calendar events are within expected bounds
        calendar_events = debug_info.get("calendar_events", [])
        
        if not calendar_events:
            self.fail("No calendar events in debug info")
        
        # Parse event dates
        event_dates = []
        for event in calendar_events:
            event_date_str = event.get("date")
            if event_date_str:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                event_dates.append(event_date)
        
        if event_dates:
            earliest = min(event_dates)
            latest = max(event_dates)
            
            print(f"Debug info shows events from {earliest.strftime('%d %b')} to {latest.strftime('%d %b')}")
            print(f"Total events in debug info: {len(calendar_events)}")
            
            # Should not go beyond June 15 of current year
            current_year = datetime.now().year
            max_expected = datetime(current_year, 6, 15)
            self.assertLessEqual(latest, max_expected, 
                f"Debug info shows events beyond expected boundary: {latest} > {max_expected}")
            
            print("✓ Debug info respects data boundaries")
        else:
            self.fail("No valid event dates found in debug info")

    def test_year_boundary_simple(self):
        """Simple test for year boundary logic without mocking (current behavior)"""
        print(f"\n=== SIMPLE YEAR BOUNDARY TEST (Current Implementation) ===")
        
        # Test what the current implementation does with these cases
        # This will fail until we implement the logic, showing what needs to be fixed
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        print(f"Current date: {datetime.now().strftime('%B %Y')} (month {current_month})")
        
        test_cases = [
            ("Week beginning 1 January", "January date"),
            ("Week beginning 15 January", "Mid January date"),
            ("Week beginning 1 December", "December date"),
            ("Week beginning 25 December", "Late December date"),
        ]
        
        for week_title, description in test_cases:
            result_date = parse_week_date(week_title)
            if result_date:
                print(f"{description:20}: {week_title:25} → {result_date.strftime('%Y-%m-%d')} (year {result_date.year})")
                
                # Analyze if this looks correct
                month_in_title = 1 if 'January' in week_title else 12  # January or December
                
                if current_month == 12 and month_in_title == 1:
                    # We're in December looking at January - should be next year
                    expected_year = current_year + 1
                    print(f"    Expected: {expected_year} (December→January should be next year)")
                elif current_month == 1 and month_in_title == 12:
                    # We're in January looking at December - should be previous year  
                    expected_year = current_year - 1
                    print(f"    Expected: {expected_year} (January→December should be previous year)")
                else:
                    # Normal case - same year
                    expected_year = current_year
                    print(f"    Expected: {expected_year} (normal case)")
                
                if result_date.year != expected_year:
                    print(f"    ⚠️  ISSUE: Got {result_date.year}, expected {expected_year}")
                else:
                    print(f"    ✓ Correct")
            else:
                print(f"{description:20}: {week_title:25} → FAILED TO PARSE")

if __name__ == "__main__":
    print("Testing actual functions from api/calendar.py")
    print("=" * 60)
    unittest.main(verbosity=2)