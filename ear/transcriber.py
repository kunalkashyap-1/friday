"""
ear/transcriber.py — faster-whisper STT + wake-word detection.

Transcribes speech segments from the Listener, checks for wake phrases,
and manages idle/active state transitions.
"""

import time
from faster_whisper import WhisperModel
from thefuzz import fuzz


class Transcriber:
    """Speech-to-text with wake-word gating."""

    # States
    IDLE = "idle"
    ACTIVE = "active"

    def __init__(self, model_size: str = "tiny", device: str = "cuda",
                 compute_type: str = "int8", wake_words: list[str] | None = None,
                 go_dark_phrases: list[str] | None = None,
                 active_timeout_s: float = 15.0):
        self.model = WhisperModel(model_size, device=device,
                                  compute_type=compute_type)
        self.wake_words = [w.lower().strip() for w in (wake_words or ["friday"])]
        self.go_dark_phrases = [p.lower().strip()
                                for p in (go_dark_phrases or ["go dark"])]
        self.active_timeout_s = active_timeout_s

        self.state = self.IDLE
        self._last_active_time: float = 0.0

    # ── transcription ─────────────────────────────────────────────
    def transcribe(self, audio_np) -> str:
        """Transcribe a numpy float32 audio array → text string."""
        segments, _ = self.model.transcribe(
            audio_np,
            beam_size=1,
            language="en",
            vad_filter=False,       # we already ran VAD upstream
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text

    # ── wake-word matching ────────────────────────────────────────
    def _contains_wake_word(self, text: str) -> tuple[bool, str]:
        """
        Check if text contains a wake phrase.
        Returns (matched, cleaned_text_after_wake_word).
        """
        lower = text.lower().strip()
        for wake in self.wake_words:
            # Exact prefix match
            if lower.startswith(wake):
                remainder = text[len(wake):].strip().lstrip(",").strip()
                return True, remainder
            # Fuzzy match on first N words (handles whisper mishearing)
            words = lower.split()
            wake_word_count = len(wake.split())
            if len(words) >= wake_word_count:
                candidate = " ".join(words[:wake_word_count])
                if fuzz.ratio(candidate, wake) >= 80:
                    remainder = " ".join(text.split()[wake_word_count:]).strip()
                    return True, remainder
        return False, text

    def _is_go_dark(self, text: str) -> bool:
        """Check if the text is a go-dark / kill-switch command."""
        lower = text.lower().strip()
        for phrase in self.go_dark_phrases:
            if phrase in lower:
                return True
            if fuzz.ratio(lower, phrase) >= 80:
                return True
        return False

    # ── state machine ─────────────────────────────────────────────
    def process(self, audio_np) -> dict:
        """
        Process an audio segment through the full pipeline.

        Returns a dict:
            {"type": "wake",      "text": ""}           — wake word only, no command
            {"type": "command",   "text": "what time"}  — a command to process
            {"type": "go_dark",   "text": ""}            — kill switch triggered
            {"type": "ignored",   "text": "..."}         — not wake-word, ignored
        """
        text = self.transcribe(audio_np)
        if not text:
            return {"type": "ignored", "text": ""}

        # ── go-dark check (always active) ─────────────────────────
        if self._is_go_dark(text):
            return {"type": "go_dark", "text": text}

        # ── timeout check ─────────────────────────────────────────
        if (self.state == self.ACTIVE
                and time.time() - self._last_active_time > self.active_timeout_s):
            self.state = self.IDLE

        # ── IDLE state: need wake word ────────────────────────────
        if self.state == self.IDLE:
            matched, remainder = self._contains_wake_word(text)
            if not matched:
                return {"type": "ignored", "text": text}

            if remainder:
                # Return one-shot command immediately, keep IDLE
                return {"type": "command", "text": remainder}
            else:
                self.state = self.ACTIVE
                self._last_active_time = time.time()
                return {"type": "wake", "text": ""}

        # ── ACTIVE state: everything is a command ─────────────────
        matched, remainder = self._contains_wake_word(text)
        command_text = remainder if matched else text
        
        if not command_text:
            self._last_active_time = time.time()
            return {"type": "wake", "text": ""}
            
        # We got a command, so drop out of active listening
        self.state = self.IDLE
        return {"type": "command", "text": command_text}

    def unload(self):
        """Free model from memory."""
        del self.model
        self.model = None

    def reset(self):
        """Return to idle state."""
        self.state = self.IDLE
