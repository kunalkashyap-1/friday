"""
ui.py — Centralized console and UI utilities using rich.
"""
from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "user": "bold cyan",
    "friday": "bold green",
    "tool": "bold yellow",
    "system": "bold magenta",
    "error": "bold red",
    "warning": "bold yellow",
})

console = Console(theme=custom_theme)

def print_user(text: str):
    console.print(f"  [user][YOU][/user] {text}")

def print_friday(text: str):
    console.print(f"  [friday][FRIDAY][/friday] {text}")

def print_tool(skill: str, text: str):
    console.print(f"  [tool][SKILL:{skill}][/tool] {text}")

def print_system(text: str):
    console.print(f"  [system]{text}[/system]")

def print_error(text: str):
    console.print(f"  [error]{text}[/error]")

def print_warning(text: str):
    console.print(f"  [warning]{text}[/warning]")
