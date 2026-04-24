"""
main.py — Friday v0.5 entry point.

Boots the full pipeline:
  mic → VAD → STT → wake-word → LLM → orchestrator → skills → TTS → speaker

Handles the main event loop and "go dark" kill switch.
"""

import sys
import yaml
import threading
from pathlib import Path

from ear.listener import Listener
from ear.transcriber import Transcriber
from brain.memory import Memory
from brain.llm import LLM
from brain.orchestrator import Orchestrator
from voice.speaker import Speaker
from skills import build_registry, get_skill_docs


# ── Banner ────────────────────────────────────────────────────────
BANNER = r"""
  ╔═══════════════════════════════════════════════════════╗
  ║                                                       ║
  ║   ███████╗██████╗ ██╗██████╗  █████╗ ██╗   ██╗       ║
  ║   ██╔════╝██╔══██╗██║██╔══██╗██╔══██╗╚██╗ ██╔╝       ║
  ║   █████╗  ██████╔╝██║██║  ██║███████║ ╚████╔╝        ║
  ║   ██╔══╝  ██╔══██╗██║██║  ██║██╔══██║  ╚██╔╝         ║
  ║   ██║     ██║  ██║██║██████╔╝██║  ██║   ██║          ║
  ║   ╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝          ║
  ║                                                       ║
  ║              v0.5 — Local Voice Assistant              ║
  ║         Say "Friday" or "Hey Friday" to begin          ║
  ╚═══════════════════════════════════════════════════════╝
"""


def load_config(path: str = "config.yaml") -> dict:
    """Load YAML configuration."""
    p = Path(path)
    if not p.exists():
        print(f"  [WARN] Config not found at {path}, using defaults.")
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def go_dark(listener, transcriber, speaker, llm, reminder_skill, timer_skill):
    """Kill switch: shut everything down, free GPU."""
    print("\n  [*] Going dark...")

    # Announce
    speaker.speak_sync("Going dark. Goodnight.")

    # Stop components
    listener.stop()
    if transcriber:
        transcriber.unload()
    speaker.stop()
    llm.unload()

    # Cancel active timers/reminders
    if timer_skill:
        timer_skill.cancel_all()
    if reminder_skill:
        reminder_skill.stop_polling()

    print("  [OFFLINE] Friday is offline. Press Enter to reboot or Ctrl+C to exit.")


def boot(config: dict):
    """Initialise all components and return them."""
    print("  [BOOT] Booting components...")

    # ── Listener (mic + VAD)
    vad_cfg = config.get("vad", {})
    listener = Listener(
        vad_threshold=vad_cfg.get("threshold", 0.5),
        silence_duration_ms=vad_cfg.get("silence_duration_ms", 1500),
    )

    # ── Transcriber (STT + wake word)
    stt_cfg = config.get("stt", {})
    transcriber = Transcriber(
        model_size=stt_cfg.get("model_size", "tiny"),
        device=stt_cfg.get("device", "cuda"),
        compute_type=stt_cfg.get("compute_type", "int8"),
        wake_words=config.get("wake_words", ["friday"]),
        go_dark_phrases=config.get("go_dark_phrases", ["go dark"]),
    )

    # ── Memory
    mem_cfg = config.get("memory", {})
    memory = Memory(max_turns=mem_cfg.get("max_turns", 50))

    # ── LLM
    llm_cfg = config.get("llm", {})
    llm = LLM(
        model=llm_cfg.get("model", "gemma4:e4b"),
        host=llm_cfg.get("host", "http://localhost:11434"),
        temperature=llm_cfg.get("temperature", 0.7),
        owner_card_path=str(Path("data") / "owner_card.yaml"),
    )

    # ── Speaker (TTS)
    tts_cfg = config.get("tts", {})
    speaker = Speaker(
        lang_code=tts_cfg.get("lang_code", "b"),
        voice=tts_cfg.get("voice", "bf_emma"),
        speed=tts_cfg.get("speed", 1.0),
    )

    # ── Skills
    skill_registry = build_registry(
        speaker=speaker, config=config, llm=llm, data_dir="data"
    )

    # Inject skill docs into LLM
    llm.set_skill_docs(get_skill_docs(skill_registry))

    # ── Orchestrator
    orchestrator = Orchestrator(
        skill_registry=skill_registry,
        llm=llm,
        memory=memory,
        speaker=speaker,
    )

    return listener, transcriber, memory, llm, speaker, skill_registry, orchestrator


def main_loop(config: dict):
    """The main Friday event loop."""
    listener, transcriber, memory, llm, speaker, skills, orchestrator = boot(config)

    # Start background services
    speaker.start()
    listener.start()
    reminder_skill = skills.get("reminder")
    timer_skill = skills.get("timer")
    if reminder_skill:
        reminder_skill.start_polling()

    print("  [MIC] Listening... (say a wake word to begin)")
    print("  [TIP] Type 'quit' to exit\n")

    try:
        while True:
            # Listen for speech
            audio = listener.listen()
            if audio is None:
                continue

            # Process through transcriber (wake-word gating)
            result = transcriber.process(audio)
            msg_type = result["type"]
            text = result["text"]

            if msg_type == "ignored":
                continue

            if msg_type == "go_dark":
                go_dark(listener, transcriber, speaker, llm,
                        reminder_skill, timer_skill)
                # Wait for reboot or exit
                try:
                    input()
                    print("  [REBOOT] Rebooting Friday...")
                    memory.clear()
                    return True  # signal to reboot
                except (KeyboardInterrupt, EOFError):
                    return False

            if msg_type == "wake":
                print("  [ACTIVE] Yes?")
                speaker.speak("Yes?")
                continue

            if msg_type == "command":
                print(f"  [YOU] {text}")

                # Add to memory and send to LLM
                memory.add("user", text)
                llm_output = llm.chat(memory.get_history(), text)
                print(f"  [LLM] {llm_output}")

                # Orchestrate (dispatch skills or speak plain text)
                response = orchestrator.handle(llm_output)
                memory.add("assistant", response)
                print(f"  [FRIDAY] {response}")
                speaker.speak(response)

    except KeyboardInterrupt:
        print("\n  [EXIT] Shutting down...")
        go_dark(listener, transcriber, speaker, llm,
                reminder_skill, timer_skill)
        return False


def main():
    print(BANNER)
    config = load_config()

    reboot = True
    while reboot:
        reboot = main_loop(config)

    print("  Goodbye!")
    sys.exit(0)


if __name__ == "__main__":
    main()
