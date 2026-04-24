"""
ear/listener.py — Microphone capture + Silero VAD.

Continuously streams mic audio at 16 kHz mono. Uses Silero VAD to detect
speech segments and yields complete utterances as numpy arrays once a
silence gap is detected.
"""

import numpy as np
import sounddevice as sd
import torch
import threading
import queue
import time


class Listener:
    """Captures mic audio and yields speech segments via Silero VAD."""

    def __init__(self, vad_threshold: float = 0.5, silence_duration_ms: int = 1500,
                 sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.vad_threshold = vad_threshold
        self.silence_samples = int(sample_rate * silence_duration_ms / 1000)
        self._audio_queue: queue.Queue = queue.Queue()
        self._running = False
        self._stream = None

        # Load Silero VAD
        self.vad_model, self.vad_utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=True,
        )
        (self._get_speech_timestamps, _, self._read_audio,
         *_rest) = self.vad_utils

    # ── mic callback ──────────────────────────────────────────────
    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio chunk."""
        if status:
            pass  # drop status warnings silently
        self._audio_queue.put(indata[:, 0].copy())

    # ── public API ────────────────────────────────────────────────
    def start(self):
        """Open the mic stream."""
        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=512,          # ~32 ms chunks
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self):
        """Close the mic stream and release resources."""
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        # flush the queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def listen(self) -> np.ndarray | None:
        """
        Block until a complete speech segment is captured.

        Returns a numpy float32 array (16 kHz mono) or None if stopped.
        The method buffers audio, runs VAD frame-by-frame, and returns
        the full utterance once silence is detected after speech.
        """
        if not self._running:
            return None

        speech_buffer: list[np.ndarray] = []
        is_speaking = False
        silence_counter = 0
        # VAD operates on 512-sample (32 ms) windows at 16 kHz
        vad_window = 512

        while self._running:
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # Run VAD on the chunk (pad/trim to vad_window)
            if len(chunk) < vad_window:
                padded = np.zeros(vad_window, dtype=np.float32)
                padded[: len(chunk)] = chunk
            else:
                padded = chunk[:vad_window]

            tensor = torch.from_numpy(padded)
            speech_prob = self.vad_model(tensor, self.sample_rate).item()

            if speech_prob >= self.vad_threshold:
                is_speaking = True
                silence_counter = 0
                speech_buffer.append(chunk)
            elif is_speaking:
                # Still capturing — count silence
                speech_buffer.append(chunk)
                silence_counter += len(chunk)
                if silence_counter >= self.silence_samples:
                    # Utterance complete
                    full_audio = np.concatenate(speech_buffer)
                    speech_buffer.clear()
                    is_speaking = False
                    silence_counter = 0
                    return full_audio

        return None
