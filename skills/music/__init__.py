"""
skills/music/__init__.py — Music skill: dispatches to the active player backend.
"""

from skills.base import BaseSkill
from skills.music.vlc_player import VLCPlayer
from skills.music.youtube_player import YouTubePlayer
from ui import print_error


class MusicSkill(BaseSkill):
    name = "music"
    description = "Play, pause, resume, stop, skip, or search music from YouTube (default) or local files."
    silent = True  # No TTS reply for music commands
    schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["play", "pause", "resume", "stop", "next", "volume", "now_playing"],
                "description": "Music action to perform.",
            },
            "query": {
                "type": "string",
                "description": "Search query (song title, artist, YouTube URL, etc.).",
            },
            "level": {
                "type": "integer",
                "description": "Volume level 0-100 (for 'volume').",
            },
        },
        "required": ["command"],
    }

    def __init__(self, music_folder: str = "", default_backend: str = "youtube"):
        self._backend_name = default_backend
        self._player = None
        if default_backend == "youtube":
            try:
                self._player = YouTubePlayer()
            except Exception as e:
                print_error(f"MUSIC YouTube init failed: {e}")
        elif default_backend == "vlc" and music_folder:
            try:
                self._player = VLCPlayer(music_folder)
            except Exception as e:
                print_error(f"MUSIC VLC init failed: {e}")

    def execute(self, params: dict) -> str:
        if not self._player:
            return "Music player not available. Check your config."
        cmd = params.get("command", "play")
        try:
            if cmd == "play":
                return self._player.play(params.get("query", ""))
            elif cmd == "pause":
                return self._player.pause()
            elif cmd == "resume":
                return self._player.resume()
            elif cmd == "stop":
                return self._player.stop()
            elif cmd == "next":
                return self._player.next_track()
            elif cmd == "volume":
                return self._player.set_volume(params.get("level", 50))
            elif cmd == "now_playing":
                return self._player.now_playing()
            else:
                return f"Unknown music command: {cmd}"
        except NotImplementedError as e:
            return str(e)

    # ── Audio ducking helpers (used by Speaker) ───────────────────
    def is_playing(self) -> bool:
        """Check if the music player is currently playing."""
        if not self._player:
            return False
        try:
            return self._player.is_playing()
        except Exception:
            return False

    def get_volume(self) -> int:
        """Get the current player volume (0-100)."""
        if not self._player:
            return 0
        try:
            return self._player.get_volume()
        except Exception:
            return 0

    def duck(self, level: int):
        """Set player volume directly (no return message). Used for TTS ducking."""
        if not self._player:
            return
        try:
            level = max(0, min(100, level))
            self._player.set_volume(level)
        except Exception:
            pass
