"""
voice/speaker.py — Kokoro TTS → sounddevice playback with audio ducking.

Generates speech audio from text using Kokoro (British English, bf_emma)
and plays it through the speakers. Queued playback prevents overlap.

When music is playing, the speaker automatically ducks the music volume
to DUCK_LEVEL before speaking and restores it afterwards.
"""

import threading
import queue
import numpy as np
import sounddevice as sd
from kokoro import KPipeline
from ui import print_error

DUCK_LEVEL = 10  # Music volume during TTS (0-100 scale)


class Speaker:
    """Text-to-speech via Kokoro with queued playback and audio ducking."""

    def __init__(self, lang_code: str = "b", voice: str = "bf_emma",
                 speed: float = 1.0, sample_rate: int = 24000):
        self.voice = voice
        self.speed = speed
        self.sample_rate = sample_rate
        self._pipeline = KPipeline(lang_code=lang_code)
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._music_skill = None  # Set via set_music_skill()

    def set_music_skill(self, music_skill):
        """
        Give the speaker a reference to the MusicSkill so it can
        duck music volume during TTS playback.
        """
        self._music_skill = music_skill

    def start(self):
        """Start the background playback thread."""
        self._running = True
        self._thread = threading.Thread(target=self._playback_loop,
                                        daemon=True, name="tts-speaker")
        self._thread.start()

    def stop(self):
        """Stop playback and shut down the thread."""
        self._running = False
        self._queue.put(None)  # sentinel to unblock
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._pipeline = None

    def speak(self, text: str):
        """
        Queue text for TTS playback.

        Non-blocking — the background thread handles synthesis + playback.
        """
        if not text or not self._running:
            return
        self._queue.put(text)

    def speak_sync(self, text: str):
        """
        Synthesise and play immediately on the calling thread.
        Useful for shutdown announcements.
        """
        if not text or not self._pipeline:
            return
        self._synthesise_and_play(text)

    # ── internal ──────────────────────────────────────────────────
    def _playback_loop(self):
        """Background thread: pulls text from queue, synthesises, plays."""
        while self._running:
            try:
                text = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if text is None:
                break

            self._synthesise_and_play(text)

    def _synthesise_and_play(self, text: str):
        """Run Kokoro synthesis and play audio through speakers."""
        if not self._pipeline:
            return

        # ── Duck music volume before speaking ─────────────────────
        ducked = False
        original_vol = None

        if self._music_skill:
            try:
                if self._music_skill.is_playing():
                    original_vol = self._music_skill.get_volume()
                    self._music_skill.duck(DUCK_LEVEL)
                    ducked = True
            except Exception:
                pass  # best-effort ducking

        try:
            audio_chunks = []
            generator = self._pipeline(text, voice=self.voice, speed=self.speed)
            for _graphemes, _phonemes, audio in generator:
                audio_chunks.append(audio)

            if audio_chunks:
                full_audio = np.concatenate(audio_chunks)
                sd.play(full_audio, samplerate=self.sample_rate)
                sd.wait()  # block until playback finishes
        except Exception as e:
            print_error(f"TTS ERROR: {e}")
        finally:
            # ── Restore music volume after speaking ───────────────
            if ducked and original_vol is not None:
                try:
                    self._music_skill.duck(original_vol)
                except Exception:
                    pass  # best-effort restore
