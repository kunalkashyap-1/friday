"""
skills/clock.py — Time and date skill.
"""

import datetime
from skills.base import BaseSkill


class ClockSkill(BaseSkill):
    name = "clock"
    description = "Get the current time or date."
    schema = {
        "query": {
            "type": "string",
            "enum": ["time", "date", "datetime"],
            "description": "What to retrieve: 'time', 'date', or 'datetime'."
        }
    }

    def execute(self, params: dict) -> str:
        now = datetime.datetime.now()
        query = params.get("query", "time").lower()

        if query == "time":
            return f"It's {now.strftime('%I:%M %p')}."
        elif query == "date":
            return f"It's {now.strftime('%A, %d %B %Y')}."
        elif query == "datetime":
            return f"It's {now.strftime('%I:%M %p on %A, %d %B %Y')}."
        else:
            return f"It's {now.strftime('%I:%M %p on %A, %d %B %Y')}."
