"""
skills/pomodoro.py — A specialized timer that runs a 25-minute work / 5-minute break cycle.
"""

import threading
from skills.base import BaseSkill
from ui import print_system

class PomodoroSkill(BaseSkill):
    name = "pomodoro"
    description = "Start, stop, or manage a Pomodoro timer (25 min work, 5 min break)."
    schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["start", "stop"],
                "description": "Whether to start or stop the pomodoro cycle.",
            },
        },
        "required": ["command"],
    }

    def __init__(self, speaker=None):
        self._speaker = speaker
        self._timer = None
        self._lock = threading.Lock()
        self._is_work_time = True
        self._is_running = False

    def execute(self, params: dict) -> str:
        command = params.get("command", "start")

        if command == "start":
            return self._start_pomodoro()
        elif command == "stop":
            return self._stop_pomodoro()
        else:
            return f"Unknown pomodoro command: {command}"

    def _start_pomodoro(self) -> str:
        with self._lock:
            if self._is_running:
                return "A Pomodoro cycle is already running."
            
            self._is_running = True
            self._is_work_time = True
            
        self._schedule_next_phase()
        return "Pomodoro started. 25 minutes of focus time begins now."

    def _stop_pomodoro(self) -> str:
        with self._lock:
            if not self._is_running:
                return "No Pomodoro cycle is currently running."
                
            if self._timer:
                self._timer.cancel()
                self._timer = None
                
            self._is_running = False
            
        return "Pomodoro cycle stopped."

    def _schedule_next_phase(self):
        with self._lock:
            if not self._is_running:
                return
                
            # 25 minutes (1500 seconds) for work, 5 minutes (300 seconds) for break
            duration = 1500 if self._is_work_time else 300
            
            self._timer = threading.Timer(duration, self._on_phase_complete)
            self._timer.daemon = True
            self._timer.start()

    def _on_phase_complete(self):
        with self._lock:
            if not self._is_running:
                return
            
            if self._is_work_time:
                msg = "Pomodoro complete! Time for a 5-minute break."
                self._is_work_time = False
            else:
                msg = "Break is over! Back to work for 25 minutes."
                self._is_work_time = True
                
        print_system(f"[POMODORO] {msg}")
        if self._speaker:
            self._speaker.speak(msg)
            
        self._schedule_next_phase()
