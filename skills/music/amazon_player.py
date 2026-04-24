"""
skills/music/amazon_player.py — Amazon Music stub.

Amazon Music has NO public API (closed beta, invite-only as of 2026).
This stub is ready for future integration once API access is granted.
"""

from skills.music.player_base import MusicPlayer


class AmazonMusicPlayer(MusicPlayer):
    """Stub — Amazon Music API is in closed beta with no public access."""

    def play(self, query="") -> str:
        raise NotImplementedError(
            "Amazon Music API is in closed beta. No public SDK available. "
            "See: https://developer.amazon.com/en-US/alexa/music"
        )

    def pause(self) -> str:
        raise NotImplementedError("Amazon Music integration pending API access.")

    def resume(self) -> str:
        raise NotImplementedError("Amazon Music integration pending API access.")

    def stop(self) -> str:
        raise NotImplementedError("Amazon Music integration pending API access.")

    def next_track(self) -> str:
        raise NotImplementedError("Amazon Music integration pending API access.")

    def set_volume(self, level: int) -> str:
        raise NotImplementedError("Amazon Music integration pending API access.")

    def now_playing(self) -> str:
        raise NotImplementedError("Amazon Music integration pending API access.")
