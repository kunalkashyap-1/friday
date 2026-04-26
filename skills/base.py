"""
skills/base.py — Abstract base class for all Friday skills.

Every skill must subclass BaseSkill and implement execute().
The registry uses `name` for dispatch and `to_ollama_tool()` to build
the native Ollama tool definitions for the chat API.
"""

from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """Abstract base for all Friday skills."""

    name: str = ""
    description: str = ""
    schema: dict = {}          # JSON Schema: {type, properties, required}
    silent: bool = False       # If True, orchestrator skips TTS for this skill

    @abstractmethod
    def execute(self, params: dict) -> str:
        """
        Execute the skill with the given parameters.

        Args:
            params: Parsed arguments dict from the tool call.

        Returns:
            A result string (will be spoken or re-fed to LLM).
        """
        ...

    def to_ollama_tool(self) -> dict:
        """Build the Ollama-compatible tool definition for this skill."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema,
            },
        }
