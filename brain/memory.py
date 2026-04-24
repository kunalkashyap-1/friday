"""
brain/memory.py — 50-turn rolling conversation memory.

Thread-safe deque that stores conversation turns for context injection
into the LLM prompt.
"""

import threading
from collections import deque


class Memory:
    """Thread-safe rolling conversation memory."""

    def __init__(self, max_turns: int = 50):
        self._history: deque[dict] = deque(maxlen=max_turns)
        self._lock = threading.Lock()

    def add(self, role: str, content: str):
        """
        Append a turn to memory.

        Args:
            role: "user", "assistant", or "system"
            content: The message content.
        """
        with self._lock:
            self._history.append({"role": role, "content": content})

    def get_history(self) -> list[dict]:
        """Return a copy of the conversation history as a list of dicts."""
        with self._lock:
            return list(self._history)

    def clear(self):
        """Wipe all memory."""
        with self._lock:
            self._history.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._history)

    def __repr__(self) -> str:
        return f"Memory(turns={len(self)}, max={self._history.maxlen})"
