"""
skills/music/__init__.py — Music skill: dispatches to the active player backend.
"""

from skills.base import BaseSkill
from skills.music.vlc_player import VLCPlayer
from skills.music.youtube_player import YouTubePlayer


class MusicSkill(BaseSkill):
    name = "music"
    description = "Play, pause, resume, stop, skip, or search music from YouTube (default) or local files."
    schema = {
        "command": {
            "type": "string",
            "enum": ["play", "pause", "resume", "stop", "next", "volume", "now_playing"],
            "description": "Music action to perform."
        },
        "query": {"type": "string", "description": "Search query (song title, artist, YouTube URL, etc.)."},
        "level": {"type": "integer", "description": "Volume level 0-100 (for 'volume')."}
    }

    def __init__(self, music_folder: str = "", default_backend: str = "youtube"):
        self._backend_name = default_backend
        self._player = None
        if default_backend == "youtube":
            try:
                self._player = YouTubePlayer()
            except Exception as e:
                print(f"  [MUSIC] YouTube init failed: {e}")
        elif default_backend == "vlc" and music_folder:
            try:
                self._player = VLCPlayer(music_folder)
            except Exception as e:
                print(f"  [MUSIC] VLC init failed: {e}")

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
