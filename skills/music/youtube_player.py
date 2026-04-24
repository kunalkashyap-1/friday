"""
skills/music/youtube_player.py — YouTube playback via yt-dlp and python-vlc.

Uses yt-dlp to search YouTube and extract the best audio stream URL,
then passes it to VLC for playback.
"""

import vlc
import yt_dlp
from skills.music.player_base import MusicPlayer


class YouTubePlayer(MusicPlayer):
    """YouTube music player using yt-dlp and python-vlc."""

    def __init__(self):
        # We use --no-video so VLC doesn't open a video window for audio streams
        self._instance = vlc.Instance("--no-video")
        self._player = self._instance.media_player_new()
        self._current_title = ""
        self._current_url = ""

    def _extract_stream(self, query: str) -> dict | None:
        """Search YouTube and extract the best audio stream info."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False, # We need the actual stream URL
        }

        search_query = f"ytsearch1:{query}" if not query.startswith("http") else query

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                # If it's a search result, grab the first entry
                if 'entries' in info and info['entries']:
                    return info['entries'][0]
                elif 'url' in info:
                    return info
        except Exception as e:
            print(f"  [YOUTUBE] yt-dlp error: {e}")
        
        return None

    def play(self, query: str = "") -> str:
        if not query:
            return "Please tell me what to play on YouTube."
        
        print(f"  [YOUTUBE] Searching for: {query}...")
        info = self._extract_stream(query)
        
        if not info or 'url' not in info:
            return f"Couldn't find or extract audio for '{query}' on YouTube."
        
        audio_url = info['url']
        self._current_title = info.get('title', 'Unknown Track')
        self._current_url = info.get('webpage_url', '')

        # Set media and play
        media = self._instance.media_new(audio_url)
        self._player.set_media(media)
        self._player.play()
        
        return f"Now playing from YouTube: {self._current_title}"

    def pause(self) -> str:
        self._player.pause()
        return "Paused."

    def resume(self) -> str:
        self._player.play()
        return "Resumed."

    def stop(self) -> str:
        self._player.stop()
        self._current_title = ""
        self._current_url = ""
        return "Stopped."

    def next_track(self) -> str:
        # For a single search result, next track doesn't make much sense without a queue system.
        return "Queue management isn't supported for YouTube yet."

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        self._player.audio_set_volume(level)
        return f"Player volume set to {level}%."

    def now_playing(self) -> str:
        if not self._player.is_playing() and not self._current_title:
            return "Nothing playing right now."
        return f"Currently playing: {self._current_title}"
