"""
skills/base.py — Abstract base class for all Friday skills.

Every skill must subclass BaseSkill and implement execute().
The registry uses `name` for dispatch and `description` + `schema`
for LLM system prompt injection.
"""

from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """Abstract base for all Friday skills."""

    name: str = ""
    description: str = ""
    schema: dict = {}

    @abstractmethod
    def execute(self, params: dict) -> str:
        """
        Execute the skill with the given parameters.

        Args:
            params: Parsed JSON dict from the ACTION:: line.

        Returns:
            A result string (will be spoken or re-fed to LLM).
        """
        ...

    def get_doc(self) -> str:
        """Generate documentation for the LLM system prompt."""
        import json
        schema_str = json.dumps(self.schema, indent=2) if self.schema else "{}"
        return (
            f"SKILL: {self.name}\n"
            f"  Description: {self.description}\n"
            f"  Parameters: {schema_str}"
        )
