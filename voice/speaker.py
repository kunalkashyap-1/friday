"""
voice/speaker.py — Kokoro TTS → sounddevice playback.

Generates speech audio from text using Kokoro (British English, bf_emma)
and plays it through the speakers. Queued playback prevents overlap.
"""

import threading
import queue
import numpy as np
import sounddevice as sd
from kokoro import KPipeline


class Speaker:
    """Text-to-speech via Kokoro with queued playback."""

    def __init__(self, lang_code: str = "b", voice: str = "bf_emma",
                 speed: float = 1.0, sample_rate: int = 24000):
        self.voice = voice
        self.speed = speed
        self.sample_rate = sample_rate
        self._pipeline = KPipeline(lang_code=lang_code)
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None

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
            print(f"  [TTS ERROR] {e}")
