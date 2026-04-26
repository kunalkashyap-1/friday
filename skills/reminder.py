"""
skills/reminder.py — JSON-file reminders with minute-poll and TTS announcements.

Persists reminders to data/reminders.json. A background thread polls every
60 seconds and fires TTS when a reminder comes due.
"""

import json
import uuid
import threading
import datetime
from pathlib import Path
from skills.base import BaseSkill
from ui import print_system, print_error


class ReminderSkill(BaseSkill):
    name = "reminder"
    description = "Set a reminder for a specific time. I'll announce it via TTS when it's due."
    schema = {
        "type": "object",
        "properties": {
            "time": {
                "type": "string",
                "description": "Time in HH:MM (24h) format.",
            },
            "message": {
                "type": "string",
                "description": "What to remind about.",
            },
            "command": {
                "type": "string",
                "enum": ["set", "list", "cancel"],
                "description": "Action: 'set' (default), 'list', or 'cancel'.",
            },
            "id": {
                "type": "string",
                "description": "Reminder ID (for cancel).",
            },
        },
        "required": ["command"],
    }

    def __init__(self, speaker=None, data_dir: str = "data"):
        self._speaker = speaker
        self._file = Path(data_dir) / "reminders.json"
        self._lock = threading.Lock()
        self._poll_thread: threading.Thread | None = None
        self._running = False

    def start_polling(self):
        """Start the background polling thread."""
        self._running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="reminder-poll"
        )
        self._poll_thread.start()

    def stop_polling(self):
        """Stop the background polling thread."""
        self._running = False

    def execute(self, params: dict) -> str:
        command = params.get("command", "set")

        if command == "set":
            return self._set_reminder(params)
        elif command == "list":
            return self._list_reminders()
        elif command == "cancel":
            return self._cancel_reminder(params.get("id", ""))
        else:
            return f"Unknown reminder command: {command}"

    # ── CRUD ──────────────────────────────────────────────────────
    def _load(self) -> list[dict]:
        with self._lock:
            if not self._file.exists():
                return []
            try:
                return json.loads(self._file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                return []

    def _save(self, reminders: list[dict]):
        with self._lock:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(
                json.dumps(reminders, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def _set_reminder(self, params: dict) -> str:
        time_str = params.get("time", "")
        message = params.get("message", "something")

        if not time_str:
            return "I need a time for the reminder (HH:MM format)."

        # Validate time format
        try:
            datetime.datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return f"'{time_str}' isn't a valid time. Use HH:MM format."

        today = datetime.date.today().isoformat()
        reminder = {
            "id": str(uuid.uuid4())[:8],
            "time": time_str,
            "date": today,
            "message": message,
            "delivered": False,
        }

        reminders = self._load()
        reminders.append(reminder)
        self._save(reminders)

        return f"Reminder set for {time_str}: '{message}' (ID: {reminder['id']})."

    def _list_reminders(self) -> str:
        reminders = self._load()
        pending = [r for r in reminders if not r.get("delivered")]
        if not pending:
            return "No pending reminders."
        lines = []
        for r in pending:
            lines.append(f"  [{r['id']}] {r['time']} — {r['message']}")
        return "Pending reminders:\n" + "\n".join(lines)

    def _cancel_reminder(self, reminder_id: str) -> str:
        if not reminder_id:
            return "I need the reminder ID to cancel it."
        reminders = self._load()
        new_list = [r for r in reminders if r["id"] != reminder_id]
        if len(new_list) == len(reminders):
            return f"No reminder found with ID '{reminder_id}'."
        self._save(new_list)
        return f"Reminder {reminder_id} cancelled."

    # ── polling ───────────────────────────────────────────────────
    def _poll_loop(self):
        """Check for due reminders every 60 seconds."""
        import time as _time
        while self._running:
            try:
                self._check_due()
            except Exception as e:
                print_error(f"REMINDER ERROR: {e}")
            _time.sleep(60)

    def _check_due(self):
        """Fire any reminders whose time has arrived."""
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.date().isoformat()

        reminders = self._load()
        changed = False

        for r in reminders:
            if r.get("delivered"):
                continue
            if r["date"] == current_date and r["time"] == current_time:
                r["delivered"] = True
                changed = True
                msg = f"Reminder: {r['message']}"
                print_system(f"[REMINDER] {msg}")
                if self._speaker:
                    self._speaker.speak(msg)

        if changed:
            self._save(reminders)
