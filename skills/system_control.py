"""
skills/system_control.py — System control actions (Lock, Sleep, Empty Recycle Bin, Screenshot).
"""

import os
import time
import subprocess
from pathlib import Path
from skills.base import BaseSkill
from ui import print_system
from PIL import ImageGrab

class SystemControlSkill(BaseSkill):
    name = "system_control"
    description = "Control the PC: lock, sleep, empty recycle bin, or take a screenshot."
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["lock", "sleep", "empty_recycle_bin", "screenshot"],
                "description": "The system action to perform.",
            },
        },
        "required": ["action"],
    }

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, params: dict) -> str:
        action = params.get("action")

        if action == "lock":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return "PC locked."
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "PC going to sleep."
        elif action == "empty_recycle_bin":
            try:
                subprocess.run(["powershell.exe", "-Command", "Clear-RecycleBin -Force"], check=True)
                return "Recycle bin emptied."
            except Exception as e:
                return f"Failed to empty recycle bin: {e}"
        elif action == "screenshot":
            try:
                timestamp = int(time.time())
                filename = f"screenshot_{timestamp}.png"
                filepath = self.data_dir / filename
                
                # Take screenshot
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
                
                print_system(f"Screenshot saved to {filepath}")
                return f"Screenshot taken and saved to {filename} in the data directory."
            except Exception as e:
                return f"Failed to take screenshot: {e}"
        else:
            return f"Unknown system action: {action}"
