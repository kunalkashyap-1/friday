"""
skills/clipboard.py — Read and write to the system clipboard.
"""

import pyperclip
from skills.base import BaseSkill

class ClipboardSkill(BaseSkill):
    name = "clipboard"
    description = "Read from or write to the system clipboard."
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write"],
                "description": "Whether to read the clipboard or write to it.",
            },
            "text": {
                "type": "string",
                "description": "The text to write to the clipboard (required if action is 'write').",
            },
        },
        "required": ["action"],
    }

    def execute(self, params: dict) -> str:
        action = params.get("action")

        if action == "read":
            content = pyperclip.paste()
            if not content:
                return "The clipboard is empty."
            return f"Clipboard content:\n{content}"
            
        elif action == "write":
            text = params.get("text", "")
            if not text:
                return "You need to provide text to write to the clipboard."
            
            pyperclip.copy(text)
            return "Text copied to clipboard."
            
        else:
            return f"Unknown clipboard action: {action}"
