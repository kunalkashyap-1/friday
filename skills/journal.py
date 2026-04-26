"""
skills/journal.py — Append quick thoughts to a running markdown file.
"""

from datetime import datetime
from pathlib import Path
from skills.base import BaseSkill
from ui import print_system

class JournalSkill(BaseSkill):
    name = "journal"
    description = "Take a note or add an entry to the journal/notepad."
    schema = {
        "type": "object",
        "properties": {
            "entry": {
                "type": "string",
                "description": "The text to add to the journal.",
            },
        },
        "required": ["entry"],
    }

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.data_dir / "journal.md"
        
        if not self.journal_file.exists():
            with open(self.journal_file, "w", encoding="utf-8") as f:
                f.write("# Friday Journal\n\n")

    def execute(self, params: dict) -> str:
        entry = params.get("entry", "").strip()
        
        if not entry:
            return "You need to tell me what to write in the journal."

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with open(self.journal_file, "a", encoding="utf-8") as f:
                f.write(f"- **{timestamp}**: {entry}\n")
                
            print_system(f"Added note to {self.journal_file}")
            return "Note added to your journal."
        except Exception as e:
            return f"Failed to write to journal: {e}"
