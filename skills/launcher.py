"""
skills/launcher.py — Opens applications natively.
"""

import os
from pathlib import Path
from skills.base import BaseSkill
from ui import print_system

class LauncherSkill(BaseSkill):
    name = "launcher"
    description = "Launch or open applications on the PC (e.g. VS Code, Spotify, notepad)."
    schema = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "The name of the application to launch (e.g. 'code', 'notepad', 'spotify').",
            },
        },
        "required": ["app_name"],
    }

    def __init__(self, apps_config: dict = None):
        """
        apps_config: Dictionary mapping application names to their executable paths.
        Example: {"spotify": "C:\\Users\\user\\AppData\\Roaming\\Spotify\\Spotify.exe"}
        """
        self.apps_config = apps_config or {}

    def execute(self, params: dict) -> str:
        app_name = params.get("app_name", "").lower()

        if not app_name:
            return "I need the name of the application to launch."

        # Check if we have a configured path
        mapped_path = None
        for key, path in self.apps_config.items():
            if key.lower() in app_name or app_name in key.lower():
                mapped_path = path
                break

        try:
            if mapped_path and Path(mapped_path).exists():
                print_system(f"Launching {app_name} from configured path: {mapped_path}")
                os.startfile(mapped_path)
                return f"Opened {app_name}."
            else:
                # Fallback to windows path resolution using 'start' command
                print_system(f"Attempting to launch {app_name} via Windows path resolution.")
                # We use start "" <app_name> to prevent the start command from interpreting the app name as a window title if it's quoted.
                os.system(f'start "" "{app_name}"')
                return f"Attempted to open {app_name}."
        except Exception as e:
            return f"Failed to open {app_name}: {e}"
