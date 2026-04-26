"""
skills/calendar.py — Read local .ics calendar files and summarize events.
"""

from pathlib import Path
from datetime import datetime, timezone
import icalendar
from skills.base import BaseSkill
from ui import print_system

class CalendarSkill(BaseSkill):
    name = "calendar"
    description = "Check the calendar for upcoming meetings or events."
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["next_events"],
                "description": "What to look for in the calendar (default: next_events).",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of events to return (default 3).",
            }
        },
        "required": [],
    }

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.ics_file = self.data_dir / "calendar.ics"

    def execute(self, params: dict) -> str:
        limit = params.get("limit", 3)
        
        if not self.ics_file.exists():
            return f"I couldn't find a calendar file. Please place a 'calendar.ics' file in the {self.data_dir} directory."

        try:
            with open(self.ics_file, "r", encoding="utf-8") as f:
                cal = icalendar.Calendar.from_ical(f.read())

            now = datetime.now(timezone.utc)
            upcoming_events = []

            for component in cal.walk():
                if component.name == "VEVENT":
                    dtstart = component.get("dtstart").dt
                    # Some ics events are dates without time
                    if type(dtstart) is not datetime:
                        # Skip full day events for "next meetings" or convert to datetime
                        # We'll just convert them to datetime with timezone to be comparable
                        dtstart = datetime.combine(dtstart, datetime.min.time()).replace(tzinfo=timezone.utc)
                    
                    if dtstart > now:
                        summary = str(component.get('summary', 'Untitled Event'))
                        upcoming_events.append((dtstart, summary))

            upcoming_events.sort(key=lambda x: x[0])
            upcoming_events = upcoming_events[:limit]

            if not upcoming_events:
                return "You have no upcoming events in your calendar."

            response = "Here are your upcoming events:\n"
            for dt, summary in upcoming_events:
                # Convert back to local time string
                local_dt = dt.astimezone()
                time_str = local_dt.strftime("%A, %b %d at %I:%M %p")
                response += f"- {time_str}: {summary}\n"
                
            return response
            
        except Exception as e:
            return f"Failed to read the calendar: {e}"
