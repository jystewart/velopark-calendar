# api/calendar.py
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Get parameters with defaults
            calendar_name = query_params.get('name', ['Lee Valley VeloPark - Road Cycling'])[0]
            include_notes = query_params.get('notes', ['true'])[0].lower() == 'true'
            weeks_ahead = int(query_params.get('weeks', ['8'])[0])
            format_type = query_params.get('format', ['ics'])[0]
            debug = query_params.get('debug', ['false'])[0].lower() == 'true'
            
            # Scrape the VeloPark website
            schedule_data = scrape_velopark_schedule()
            
            if debug or format_type == 'debug':
                # Return detailed debug information
                debug_info = generate_debug_info(schedule_data, weeks_ahead)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(debug_info, indent=2, default=str).encode())
            elif format_type == 'json':
                # Return JSON for debugging
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(schedule_data, indent=2).encode())
            else:
                # Generate and return iCalendar
                ics_content = generate_icalendar(schedule_data, calendar_name, include_notes, weeks_ahead)
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/calendar; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="velopark-schedule.ics"')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(ics_content.encode('utf-8'))
                
        except Exception as e:
            # Return error response
            error_message = f"Error: {str(e)}"
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_message.encode())

def scrape_velopark_schedule():
    """Scrape the Lee Valley VeloPark website for opening hours"""
    url = "https://www.better.org.uk/leisure-centre/lee-valley/velopark/road-cycling"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the schedule section
        schedule_section = soup.find('section', class_='activity-theme__third-width')
        
        if not schedule_section:
            raise Exception("Could not find schedule section on the website")
        
        schedule_data = {}
        
        # Find all week sections within the schedule
        week_sections = schedule_section.find_all('div', class_='activity-theme__third-width-text-only')
        
        for section in week_sections:
            # Get the week heading
            heading = section.find('h3')
            if not heading:
                continue
                
            week_title = heading.get_text(strip=True)
            
            # Find the list of opening hours
            hours_list = section.find('ul')
            if not hours_list:
                continue
            
            week_data = {}
            list_items = hours_list.find_all('li')
            
            for item in list_items:
                text = item.get_text(strip=True)
                # Parse "Monday - 07:00 - 21:00" format
                parts = text.split(' - ', 1)
                if len(parts) >= 2:
                    day = parts[0].strip()
                    times = parts[1].strip()
                    week_data[day] = times
            
            if week_data:
                schedule_data[week_title] = week_data
        
        if not schedule_data:
            raise Exception("No schedule data found on the website")
            
        return schedule_data
        
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch website: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to parse schedule: {str(e)}")

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

def generate_icalendar(schedule_data, calendar_name, include_notes, weeks_ahead):
    """Generate iCalendar content from schedule data"""
    
    # iCalendar header
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Lee Valley VeloPark//Road Cycling Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{calendar_name}",
        "X-WR-CALDESC:Lee Valley VeloPark Road Cycling opening hours - Auto-updated from website",
        "X-WR-TIMEZONE:Europe/London"
    ]
    
    event_count = 0
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Process each week in the schedule data (only generate events for weeks with actual data)
    for week_title, week_data in schedule_data.items():
        week_start_date = parse_week_date(week_title)
        if not week_start_date:
            continue
        
        # Only generate events for this specific week (no repetition beyond available data)
        for day_name, times_str in week_data.items():
            if day_name not in day_names:
                continue
            
            day_index = day_names.index(day_name)
            event_date = week_start_date + timedelta(days=day_index)
            
            # Parse time slots for this day
            time_slots = parse_time_slots(times_str)
            special_notes = extract_special_notes(times_str)
            
            # Create events for each time slot
            for slot_index, (start_time, end_time) in enumerate(time_slots):
                event_count += 1
                
                # Format date and time for iCalendar
                date_str = event_date.strftime('%Y%m%d')
                start_time_str = start_time.replace(':', '')
                end_time_str = end_time.replace(':', '')
                
                # Create unique ID
                uid = f"velopark-{date_str}-{start_time_str}-{slot_index}@leovalley.org.uk"
                
                # Create summary
                summary = "Lee Valley VeloPark - Road Circuit Open"
                if len(time_slots) > 1:
                    summary += f" (Session {slot_index + 1})"
                
                # Create description
                description = "Road cycling circuit is open for sessions and activities. Last entry one hour before closing."
                if include_notes and special_notes:
                    description += f" {special_notes}"
                
                # Current timestamp
                now_str = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                
                # Add event to calendar
                ics_lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTART:{date_str}T{start_time_str}00",
                    f"DTEND:{date_str}T{end_time_str}00",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:{description}",
                    "LOCATION:Lee Valley VeloPark, Abercrombie Road, Queen Elizabeth Olympic Park, London E20 3AB",
                    "URL:https://www.better.org.uk/leisure-centre/lee-valley/velopark/road-cycling",
                    f"DTSTAMP:{now_str}",
                    "END:VEVENT"
                ])
    
    # Close calendar
    ics_lines.append("END:VCALENDAR")
    
    return "\r\n".join(ics_lines)

def generate_debug_info(schedule_data, weeks_ahead):
    """Generate detailed debug information for troubleshooting"""
    debug_info = {
        "schedule_data": schedule_data,
        "parsing_results": {},
        "calendar_events": [],
        "issues_found": []
    }
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Process each week and show parsing details
    for week_title, week_data in schedule_data.items():
        week_start_date = parse_week_date(week_title)
        
        debug_info["parsing_results"][week_title] = {
            "week_start_date": week_start_date,
            "days": {}
        }
        
        if not week_start_date:
            debug_info["issues_found"].append(f"Could not parse week date: {week_title}")
            continue
        
        for day_name, times_str in week_data.items():
            if day_name not in day_names:
                continue
            
            day_index = day_names.index(day_name)
            event_date = week_start_date + timedelta(days=day_index)
            
            # Parse time slots and show details
            time_slots = parse_time_slots(times_str)
            special_notes = extract_special_notes(times_str)
            
            day_debug = {
                "original_text": times_str,
                "parsed_slots": time_slots,
                "special_notes": special_notes,
                "event_date": event_date,
                "day_of_week": event_date.strftime('%A')
            }
            
            debug_info["parsing_results"][week_title]["days"][day_name] = day_debug
            
            # Check for specific issues
            if day_name == "Friday" and "07:00-14:00 16:00-21:00" in times_str:
                if len(time_slots) != 2:
                    debug_info["issues_found"].append(
                        f"Friday parsing issue: expected 2 slots, got {len(time_slots)} for '{times_str}'"
                    )
            
            # Generate events for this day
            for slot_index, (start_time, end_time) in enumerate(time_slots):
                summary = "Lee Valley VeloPark - Road Circuit Open"
                if len(time_slots) > 1:
                    summary += f" (Session {slot_index + 1})"
                
                event = {
                    "date": event_date.strftime('%Y-%m-%d'),
                    "day_name": day_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "summary": summary,
                    "session_number": slot_index + 1,
                    "total_sessions": len(time_slots),
                    "original_text": times_str,
                    "special_notes": special_notes
                }
                
                debug_info["calendar_events"].append(event)
    
    # Add summary statistics
    debug_info["summary"] = {
        "total_weeks": len(schedule_data),
        "total_events": len(debug_info["calendar_events"]),
        "issues_count": len(debug_info["issues_found"])
    }
    
    return debug_info