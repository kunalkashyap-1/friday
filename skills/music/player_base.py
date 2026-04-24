"""
skills/music/player_base.py — Abstract music player interface.

All player backends (VLC, Spotify, Amazon) implement this ABC.
"""

from abc import ABC, abstractmethod


class MusicPlayer(ABC):
    """Interface for music playback backends."""

    @abstractmethod
    def play(self, query: str = "") -> str:
        """Play a track matching the query, or random if empty."""
        ...

    @abstractmethod
    def pause(self) -> str:
        """Pause playback."""
        ...

    @abstractmethod
    def resume(self) -> str:
        """Resume playback."""
        ...

    @abstractmethod
    def stop(self) -> str:
        """Stop playback completely."""
        ...

    @abstractmethod
    def next_track(self) -> str:
        """Skip to next track."""
        ...

    @abstractmethod
    def set_volume(self, level: int) -> str:
        """Set player volume (0-100)."""
        ...

    @abstractmethod
    def now_playing(self) -> str:
        """Return info about the currently playing track."""
        ...
