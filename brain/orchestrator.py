"""
brain/orchestrator.py — Parses ACTION::SKILL::JSON and dispatches to skills.

Handles the full flow:
1. Parse LLM output for ACTION:: lines
2. Look up the skill in the registry
3. Execute the skill
4. Optionally re-feed the result to the LLM for a spoken summary
5. Hand plain-text responses directly to TTS
"""

import re
import json


# Regex: ACTION::skill_name::{"key": "value", ...}
ACTION_PATTERN = re.compile(r"^ACTION::(\w+)::(.+)$", re.MULTILINE)


class Orchestrator:
    """Parses LLM output and dispatches skill calls."""

    def __init__(self, skill_registry: dict, llm=None, memory=None, speaker=None):
        """
        Args:
            skill_registry: dict mapping skill name → BaseSkill instance.
            llm: LLM instance (for re-feeding skill results).
            memory: Memory instance.
            speaker: Speaker instance for TTS.
        """
        self.skills = skill_registry
        self.llm = llm
        self.memory = memory
        self.speaker = speaker

    def handle(self, llm_output: str) -> str:
        """
        Process the raw LLM output.

        Returns:
            Final text response to speak aloud.
        """
        matches = ACTION_PATTERN.findall(llm_output)

        if not matches:
            # Pure conversational response — speak it directly
            return llm_output

        results = []
        for skill_name, json_str in matches:
            result = self._dispatch(skill_name, json_str)
            results.append(result)

        # If there were action lines, combine results
        combined_result = "\n".join(results)

        # Strip any non-ACTION text from the original output (preamble/postamble)
        plain_parts = ACTION_PATTERN.sub("", llm_output).strip()

        # If the LLM also wrote plain text alongside actions, prepend it
        if plain_parts:
            return f"{plain_parts}\n{combined_result}"

        # Re-feed skill results to LLM for a natural spoken summary
        if self.llm and self.memory:
            followup_prompt = (
                f"The following skill(s) just ran. Summarise the result in ONE "
                f"witty sentence for me to hear:\n{combined_result}"
            )
            summary = self.llm.chat(self.memory.get_history(), followup_prompt)

            # If the summary itself contains more ACTION lines, just use raw result
            if "ACTION::" in summary:
                return combined_result
            return summary

        return combined_result

    def _dispatch(self, skill_name: str, json_str: str) -> str:
        """Look up and execute a single skill."""
        skill = self.skills.get(skill_name)
        if not skill:
            return f"Sorry, I don't have a skill called '{skill_name}'."

        try:
            params = json.loads(json_str)
        except json.JSONDecodeError as e:
            return f"Couldn't parse parameters for {skill_name}: {e}"

        try:
            result = skill.execute(params)
            return result
        except Exception as e:
            return f"Skill '{skill_name}' hit an error: {e}"
