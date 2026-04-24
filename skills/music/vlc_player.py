"""
skills/music/vlc_player.py — Local music playback via python-vlc.

Scans a music folder for audio files, fuzzy-matches artist/album/title,
and plays via VLC. Supports shuffle for "random" queries.
"""

import os
import random
from pathlib import Path
import vlc
from thefuzz import fuzz
from skills.music.player_base import MusicPlayer

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma"}


class VLCPlayer(MusicPlayer):
    """Local music player using python-vlc."""

    def __init__(self, music_folder: str):
        self._folder = Path(music_folder)
        self._instance = vlc.Instance("--no-xlib")
        self._player = self._instance.media_player_new()
        self._playlist: list[Path] = []
        self._current_index = 0
        self._scan_library()

    def _scan_library(self):
        """Recursively find all audio files in the music folder."""
        self._library: list[Path] = []
        if not self._folder.exists():
            return
        for root, _dirs, files in os.walk(self._folder):
            for f in files:
                if Path(f).suffix.lower() in AUDIO_EXTENSIONS:
                    self._library.append(Path(root) / f)

    def _fuzzy_search(self, query: str) -> list[Path]:
        """Fuzzy-match query against filenames and parent directories."""
        if not query or query.lower() in ("random", "shuffle", "anything"):
            shuffled = self._library.copy()
            random.shuffle(shuffled)
            return shuffled

        scored = []
        q = query.lower()
        for path in self._library:
            name = path.stem.lower()
            parent = path.parent.name.lower()
            full = f"{parent} {name}"
            score = max(fuzz.partial_ratio(q, name),
                        fuzz.partial_ratio(q, parent),
                        fuzz.partial_ratio(q, full))
            if score >= 55:
                scored.append((score, path))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    def play(self, query: str = "") -> str:
        matches = self._fuzzy_search(query)
        if not matches:
            return f"No tracks found matching '{query}'."
        self._playlist = matches
        self._current_index = 0
        return self._play_current()

    def _play_current(self) -> str:
        if not self._playlist:
            return "Playlist is empty."
        track = self._playlist[self._current_index]
        media = self._instance.media_new(str(track))
        self._player.set_media(media)
        self._player.play()
        return f"Now playing: {track.stem} ({track.parent.name})"

    def pause(self) -> str:
        self._player.pause()
        return "Paused."

    def resume(self) -> str:
        self._player.play()
        return "Resumed."

    def stop(self) -> str:
        self._player.stop()
        self._playlist.clear()
        return "Stopped."

    def next_track(self) -> str:
        if not self._playlist:
            return "No playlist active."
        self._current_index = (self._current_index + 1) % len(self._playlist)
        return self._play_current()

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        self._player.audio_set_volume(level)
        return f"Player volume set to {level}%."

    def now_playing(self) -> str:
        if not self._playlist:
            return "Nothing playing."
        if not self._player.is_playing():
            return "Nothing playing right now."
        track = self._playlist[self._current_index]
        return f"Currently playing: {track.stem} ({track.parent.name})"
