"""
brain/orchestrator.py — Native Ollama tool-call dispatcher.

Handles the full flow:
1. Receive the LLM response message (from llm.chat)
2. If tool_calls are present: execute skills, feed results back to LLM
3. If all triggered skills are silent (music/volume): skip TTS
4. Otherwise: LLM generates a natural spoken summary
5. If no tool_calls: return the plain text response for TTS
"""

import json
from ui import print_tool


class Orchestrator:
    """Dispatches Ollama tool calls to skills and manages the feedback loop."""

    def __init__(self, skill_registry: dict, llm=None, memory=None, speaker=None):
        """
        Args:
            skill_registry: dict mapping skill name → BaseSkill instance.
            llm: LLM instance (for tool-result feedback).
            memory: Memory instance.
            speaker: Speaker instance for TTS.
        """
        self.skills = skill_registry
        self.llm = llm
        self.memory = memory
        self.speaker = speaker

    def handle(self, user_text: str, history: list[dict]) -> tuple[str, bool]:
        """
        Full tool-calling loop.

        1. Send user text + tools to LLM
        2. If tool_calls → execute → feed results back → get summary
        3. If silent skills only → return result with should_speak=False
        4. If plain text → return for TTS

        Returns:
            (response_text, should_speak) — should_speak is False for
            silent skills like music/volume.
        """
        # Step 1: Initial LLM call with tools
        response_msg = self.llm.chat(history, user_text)

        # Step 2: Check for tool calls
        tool_calls = getattr(response_msg, "tool_calls", None)
        
        # DEBUG
        # print(f"  [DEBUG LLM] content={repr(response_msg.content)}")
        # print(f"  [DEBUG LLM] tool_calls={repr(tool_calls)}")

        if not tool_calls:
            # Pure conversational response — speak it
            text = response_msg.content or ""
            return text.strip(), True

        # Step 3: Execute each tool call
        results = []
        all_silent = True

        for tc in tool_calls:
            func = tc.function
            skill_name = func.name
            arguments = func.arguments or {}

            skill = self.skills.get(skill_name)
            if not skill:
                results.append({
                    "name": skill_name,
                    "result": f"Unknown skill: '{skill_name}'",
                    "silent": False,
                })
                all_silent = False
                continue

            if not skill.silent:
                all_silent = False

            try:
                result = skill.execute(arguments)
            except Exception as e:
                result = f"Skill '{skill_name}' error: {e}"

            results.append({
                "name": skill_name,
                "result": result,
                "silent": skill.silent,
            })
            print_tool(skill_name, str(result).encode('ascii', 'ignore').decode())

        # Step 4: If ALL skills are silent → return combined result, no TTS
        if all_silent:
            combined = "\n".join(r["result"] for r in results)
            return combined, False

        # Step 5: Feed tool results back to LLM for a natural spoken summary
        if self.llm:
            # Build the full conversation for the feedback call
            feedback_messages = [
                {"role": "system", "content": self.llm._build_system_prompt()}
            ]
            feedback_messages.extend(history)
            feedback_messages.append({"role": "user", "content": user_text})

            # Add the assistant's tool-call message
            feedback_messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or {},
                        }
                    }
                    for tc in tool_calls
                ],
            })

            # Add each tool result
            for r in results:
                feedback_messages.append({
                    "role": "tool",
                    "content": r["result"],
                    "tool_name": r["name"],
                })

            # Get the summary (no tools this time to avoid infinite loop)
            summary_msg = self.llm.chat_with_history(
                feedback_messages, use_tools=False
            )
            summary = (summary_msg.content or "").strip()

            # Safety: if the summary is empty, fall back to raw results
            if summary:
                return summary, True

        # Fallback: return raw results
        return "\n".join(r["result"] for r in results), True
