"""
skills/__init__.py — Auto-discovery skill registry.

Imports all skill modules, finds BaseSkill subclasses, instantiates them,
and exposes SKILL_REGISTRY + combined Ollama tool definitions.
"""

from skills.base import BaseSkill

# Import all skill modules so their classes get registered
from skills import (
    clock, timer, reminder, dice, camera, volume, web_search,
    system_control, launcher, clipboard, journal, calendar, pomodoro
)
from skills.music import MusicSkill


def build_registry(**kwargs) -> dict[str, BaseSkill]:
    """
    Instantiate all skills and return a name → instance registry.

    kwargs are forwarded to skills that need external deps
    (e.g. speaker for timer/reminder, config for music).
    """
    speaker = kwargs.get("speaker")
    config = kwargs.get("config", {})

    registry: dict[str, BaseSkill] = {}

    # Clock
    registry["clock"] = clock.ClockSkill()

    # Timer (needs speaker for TTS announcements)
    registry["timer"] = timer.TimerSkill(speaker=speaker)

    # Reminder (needs speaker for TTS announcements)
    data_dir = kwargs.get("data_dir", "data")
    registry["reminder"] = reminder.ReminderSkill(
        speaker=speaker, data_dir=data_dir
    )

    # Dice / coin / random
    registry["dice"] = dice.DiceSkill()

    # Camera (needs LLM for vision queries)
    llm = kwargs.get("llm")
    cam_index = config.get("camera", {}).get("device_index", 0)
    registry["camera"] = camera.CameraSkill(llm=llm, device_index=cam_index)

    # Volume
    registry["volume"] = volume.VolumeSkill()

    # Music
    music_cfg = config.get("music", {})
    registry["music"] = MusicSkill(
        music_folder=music_cfg.get("folder", ""),
        default_backend=music_cfg.get("default_backend", "vlc"),
    )

    # Web Search
    ws_cfg = config.get("web_search", {})
    registry["web_search"] = web_search.WebSearchSkill(
        max_results=ws_cfg.get("max_results", 3),
    )

    # System Control
    registry["system_control"] = system_control.SystemControlSkill(data_dir=data_dir)

    # Launcher
    apps_cfg = config.get("apps", {})
    registry["launcher"] = launcher.LauncherSkill(apps_config=apps_cfg)

    # Clipboard
    registry["clipboard"] = clipboard.ClipboardSkill()

    # Journal
    registry["journal"] = journal.JournalSkill(data_dir=data_dir)

    # Calendar
    registry["calendar"] = calendar.CalendarSkill(data_dir=data_dir)

    # Pomodoro
    registry["pomodoro"] = pomodoro.PomodoroSkill(speaker=speaker)

    return registry


def get_ollama_tools(registry: dict[str, BaseSkill]) -> list[dict]:
    """Build the list of Ollama tool definitions from the skill registry."""
    return [skill.to_ollama_tool() for skill in registry.values()]
