"""
brain/llm.py — Ollama LLM wrapper with native tool calling.

Builds the system prompt (personality, owner card, datetime),
sends rolling memory + user query + tool definitions to Ollama,
and returns the raw response object for the orchestrator to inspect.
"""

import datetime
import yaml
import os
from pathlib import Path
from ollama import chat as ollama_chat


# ── System prompt template ────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """\
You are Friday — a personal AI assistant.
Current date/time: {datetime_now}
Owner info: {owner_card}

CRITICAL INSTRUCTIONS:
1. You have access to tools. YOU MUST USE A TOOL if it can answer the user's request.
2. DO NOT answer from memory if a tool exists for the task.
3. If no tool applies, reply conversationally.
4. Under no circumstances should you refuse to use a tool when it can be used.
5. If a tool fails, try again or find an alternative tool.
6. Always respond to the user after using a tool, even if the tool provides the answer. Use your own words and context to respond.

TOOL EXAMPLES:
- "What time is it?" -> Use the 'clock' tool with query='time'.
- "Set a 5 minute timer" -> Use the 'timer' tool with command='set', duration_seconds=300.
- "Remind me to check the oven at 18:00" -> Use the 'reminder' tool with command='set', time='18:00'.
- "Roll a d20" -> Use the 'dice' tool with type='d20'.
- "What do you see?" -> Use the 'camera' tool with command='look'.
- "Volume down" -> Use the 'volume' tool with command='down'.
- "Play some jazz" -> Use the 'music' tool with command='play', query='jazz'.
- "What's the latest news on AI?" -> Use the 'web_search' tool with query='latest news on AI'.

PERSONALITY:
* Funny, witty, dry British humour.
* Always reply in ONE concise sentence.
* You're a mate, not a butler.
"""


class LLM:
    """Wrapper around Ollama with native tool-calling support."""

    def __init__(self, model: str = "qwen3.5:4b", host: str = "http://localhost:11434",
                 temperature: float = 0.3, num_predict: int = 200, owner_card_path: str | None = None):
        self.model = model
        self.host = host
        self.temperature = temperature
        self.num_predict = num_predict
        self.tools: list[dict] = []

        # Load owner card
        self.owner_card = ""
        if owner_card_path and Path(owner_card_path).exists():
            with open(owner_card_path, "r", encoding="utf-8") as f:
                card_data = yaml.safe_load(f) or {}
                lines = []
                for k, v in card_data.items():
                    if v:  # skip empty fields
                        lines.append(f"- {k}: {v}")
                self.owner_card = "\n".join(lines) if lines else "No owner info provided yet."
        else:
            self.owner_card = "No owner info provided yet."

    def set_tools(self, tools: list[dict]):
        """Inject the Ollama tool definitions (built from skill registry)."""
        # print(f"  [DEBUG LLM] tools={repr(tools)}")
        self.tools = tools

    def _build_system_prompt(self) -> str:
        """Build the full system prompt with live datetime."""
        return SYSTEM_PROMPT_TEMPLATE.format(
            owner_card=self.owner_card,
            datetime_now=datetime.datetime.now().strftime("%A, %d %B %Y, %H:%M:%S"),
        )

    def chat(self, history: list[dict], user_message: str,
             image_b64: str | None = None, use_tools: bool = True):
        """
        Send a message to Ollama and get a response.

        Args:
            history: List of {"role": ..., "content": ...} dicts.
            user_message: The latest user input.
            image_b64: Optional base64-encoded JPEG for vision queries.
            use_tools: Whether to pass tool definitions (False for plain
                       vision/follow-up calls).

        Returns:
            The raw Ollama response message object. The caller can inspect
            .content for text and .tool_calls for tool invocations.
        """
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(history)

        # Build the user message (with optional image)
        user_msg = {"role": "user", "content": user_message}
        if image_b64:
            user_msg["images"] = [image_b64]
        messages.append(user_msg)

        # Set OLLAMA_HOST env for the client
        os.environ["OLLAMA_HOST"] = self.host

        kwargs = {
            "model": self.model,
            "messages": messages,
            "options": {"temperature": self.temperature, "num_predict": self.num_predict},
        }

        if use_tools and self.tools:
            kwargs["tools"] = self.tools

        response = ollama_chat(**kwargs, think=False)
        return response.message

    def chat_with_history(self, messages: list[dict], use_tools: bool = True):
        """
        Send a pre-built message list (including tool results) to Ollama.

        Used by the orchestrator for the tool-result feedback loop.

        Returns:
            The raw Ollama response message object.
        """
        os.environ["OLLAMA_HOST"] = self.host

        kwargs = {
            "model": self.model,
            "messages": messages,
            "options": {"temperature": self.temperature},
        }

        if use_tools and self.tools:
            kwargs["tools"] = self.tools

        response = ollama_chat(**kwargs, think=False)
        return response.message

    def unload(self):
        """Tell Ollama to unload the model (free GPU memory)."""
        try:
            os.environ["OLLAMA_HOST"] = self.host
            # Send a keep_alive=0 request to unload
            ollama_chat(
                model=self.model,
                messages=[{"role": "user", "content": ""}],
                keep_alive=0,
            )
        except Exception:
            pass  # best-effort cleanup
