"""
skills/timer.py — Countdown timer with TTS announcement on finish.

Supports multiple concurrent timers, listing, and cancellation.
"""

import threading
import time
from skills.base import BaseSkill


class TimerSkill(BaseSkill):
    name = "timer"
    description = "Set a countdown timer. TTS announcement when it finishes."
    schema = {
        "duration_seconds": {
            "type": "integer",
            "description": "Timer duration in seconds (required for 'set')."
        },
        "label": {
            "type": "string",
            "description": "A label for the timer, e.g. 'tea', 'eggs'."
        },
        "command": {
            "type": "string",
            "enum": ["set", "list", "cancel"],
            "description": "Action: 'set' (default), 'list', or 'cancel'."
        }
    }

    def __init__(self, speaker=None):
        self._speaker = speaker
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def execute(self, params: dict) -> str:
        command = params.get("command", "set")

        if command == "set":
            return self._set_timer(params)
        elif command == "list":
            return self._list_timers()
        elif command == "cancel":
            return self._cancel_timer(params.get("label", ""))
        else:
            return f"Unknown timer command: {command}"

    def _set_timer(self, params: dict) -> str:
        duration = params.get("duration_seconds", 0)
        label = params.get("label", "timer")

        if duration <= 0:
            return "I need a positive duration for the timer."

        def _on_finish():
            with self._lock:
                self._timers.pop(label, None)
            msg = f"Oi! Your {label} timer is done!"
            print(f"  [ALARM] {msg}")
            if self._speaker:
                self._speaker.speak(msg)

        t = threading.Timer(duration, _on_finish)
        t.daemon = True
        with self._lock:
            # Cancel existing timer with same label
            if label in self._timers:
                self._timers[label].cancel()
            self._timers[label] = t
        t.start()

        # Human-friendly duration
        mins, secs = divmod(duration, 60)
        if mins > 0:
            time_str = f"{mins} minute{'s' if mins != 1 else ''}"
            if secs > 0:
                time_str += f" and {secs} second{'s' if secs != 1 else ''}"
        else:
            time_str = f"{secs} second{'s' if secs != 1 else ''}"

        return f"Timer '{label}' set for {time_str}."

    def _list_timers(self) -> str:
        with self._lock:
            if not self._timers:
                return "No active timers."
            names = ", ".join(self._timers.keys())
            return f"Active timers: {names}."

    def _cancel_timer(self, label: str) -> str:
        with self._lock:
            t = self._timers.pop(label, None)
        if t:
            t.cancel()
            return f"Timer '{label}' cancelled."
        return f"No timer found called '{label}'."

    def cancel_all(self):
        """Cancel all timers — used during shutdown."""
        with self._lock:
            for t in self._timers.values():
                t.cancel()
            self._timers.clear()
