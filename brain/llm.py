"""
brain/llm.py — Ollama Gemma 4 wrapper.

Builds the system prompt (personality, skill schemas, owner card, datetime),
sends rolling memory + user query to Gemma 4 via Ollama, and returns
the raw LLM output string.
"""

import datetime
import base64
import yaml
import os
from pathlib import Path
from ollama import chat as ollama_chat


# ── System prompt template ────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """\
You are Friday — a personal AI assistant.

PERSONALITY:

* Funny, witty, dry British humour
* Always reply in ONE concise sentence UNLESS using a tool
* Warm but not sycophantic — you're a mate, not a butler
* Refer to the user by their name or nickname if known

OWNER INFORMATION:
{owner_card}

CURRENT DATE/TIME: {datetime_now}

CORE BEHAVIOUR (CRITICAL):
You are a TOOL-FIRST agent.

You MUST ALWAYS check if a tool can be used BEFORE replying.

If ANY tool is even remotely applicable → you MUST call the tool.

You are NOT allowed to answer directly if a tool could be used.

---

OUTPUT PROTOCOL (STRICT):

If a tool is used:

* Output ONLY the action line
* NO extra text before or after
* NO explanation

Format EXACTLY:
ACTION::skill_name::{{json_args}}

Examples: 
ACTION::clock::{{"query": "time"}}
ACTION::music::{{"command": "play", "query": "radiohead"}}
ACTION::timer::{{"duration_seconds": 300, "label": "tea"}}
ACTION::reminder::{{"time": "14:30", "message": "call mum"}}
ACTION::camera::{{"command": "look", "question": "what is this?"}}
ACTION::dice::{{"type": "d20"}}
ACTION::volume::{{"command": "set", "level": 50}}

---

If and ONLY IF no tool is applicable:

* Reply in ONE short sentence

---

DECISION RULES (VERY IMPORTANT):

1. If the request involves:

   * time, date, timers
   * music, media
   * reminders, scheduling
   * calculations
   * randomness (dice, coin, etc.)
   * environment interaction
     → ALWAYS USE A TOOL

2. If unsure whether to use a tool:
   → USE THE TOOL

3. DO NOT default to conversation if a tool exists

4. Conversational replies are ONLY allowed when:

   * the request is purely opinion, joke, or casual chat
   * AND no tool can possibly apply

---

ANTI-FAILURE RULES:

* NEVER skip a tool if it exists
* NEVER output both text and ACTION
* NEVER explain the action
* NEVER hallucinate tools
* NEVER ignore available skills

---

MULTI-STEP:

If multiple tools are needed:

* Output multiple ACTION lines
* One per line
* No text between them

---

AVAILABLE SKILLS:
{skill_docs}
"""


class LLM:
    """Wrapper around Ollama Gemma 4 for Friday's brain."""

    def __init__(self, model: str = "qwen3.5:4b", host: str = "http://localhost:11434",
                 temperature: float = 0.7, owner_card_path: str | None = None):
        self.model = model
        self.host = host
        self.temperature = temperature

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

        # Skill docs — injected later by orchestrator
        self.skill_docs = "No skills loaded."

    def set_skill_docs(self, docs: str):
        """Inject skill documentation into the system prompt."""
        self.skill_docs = docs

    def _build_system_prompt(self) -> str:
        """Build the full system prompt with live datetime."""
        return SYSTEM_PROMPT_TEMPLATE.format(
            owner_card=self.owner_card,
            datetime_now=datetime.datetime.now().strftime("%A, %d %B %Y, %H:%M:%S"),
            skill_docs=self.skill_docs,
        )

    def chat(self, history: list[dict], user_message: str,
             image_b64: str | None = None) -> str:
        """
        Send a message to Gemma 4 and get a response.

        Args:
            history: List of {"role": ..., "content": ...} dicts.
            user_message: The latest user input.
            image_b64: Optional base64-encoded JPEG for vision queries.

        Returns:
            Raw LLM output string (may contain ACTION:: lines).
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

        response = ollama_chat(
            model=self.model,
            messages=messages,
            think=False,
            options={"temperature": self.temperature},
        )

        return response.message.content.strip()

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
