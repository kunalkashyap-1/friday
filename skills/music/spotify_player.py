"""
skills/music/spotify_player.py — Spotify stub (not yet implemented).
"""

from skills.music.player_base import MusicPlayer


class SpotifyPlayer(MusicPlayer):
    """Stub — Spotify integration pending."""

    def play(self, query="") -> str:
        raise NotImplementedError("Spotify integration not yet implemented.")

    def pause(self) -> str:
        raise NotImplementedError("Spotify integration not yet implemented.")

    def resume(self) -> str:
        raise NotImplementedError("Spotify integration not yet implemented.")

    def stop(self) -> str:
        raise NotImplementedError("Spotify integration not yet implemented.")

    def next_track(self) -> str:
        raise NotImplementedError("Spotify integration not yet implemented.")

    def set_volume(self, level: int) -> str:
        raise NotImplementedError("Spotify integration not yet implemented.")

    def now_playing(self) -> str:
        raise NotImplementedError("Spotify integration not yet implemented.")
