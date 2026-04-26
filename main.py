"""
main.py — Friday v0.5 entry point.

Boots the full pipeline:
  mic → VAD → STT → wake-word → LLM → orchestrator → skills → TTS → speaker

Handles the main event loop and "go dark" kill switch.
"""

# ── Suppress noisy third-party warnings ──────────────────────────
import warnings
warnings.filterwarnings("ignore", message=".*weight_norm.*is deprecated.*")
warnings.filterwarnings("ignore", message=".*dropout option adds dropout.*")
warnings.filterwarnings("ignore", message=".*Defaulting repo_id.*")

import sys
import yaml
import threading
import queue
from pathlib import Path
import random

from ear.listener import Listener
from ear.transcriber import Transcriber
from brain.memory import Memory
from brain.llm import LLM
from brain.orchestrator import Orchestrator
from voice.speaker import Speaker
from skills import build_registry, get_ollama_tools
from ui import console, print_user, print_friday, print_system, print_warning, print_error


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
SIGN_OFFS = [
    "Going dark. Goodnight.",
    "Signing off for the night.",
    "Shutting down. See you tomorrow.",
    
    "Alright, I’m off. Sleep well!",
    "Calling it a night—rest up!",
    "Time to log off. Catch you later!",
    
    "Powering down… dream mode activated.",
    "Lights out on my end. Goodnight!",
    "System entering sleep mode",
    
    "And so, I fade into the quiet… goodnight.",
    "The night takes over. I’m gone.",
    "Curtains closed. Until next time.",
    
    "Initiating shutdown sequence. Goodnight.",
    "All processes halted. See you soon.",
    "Session terminated. Rest well.",
    
    "Yep, I’m done here. Goodnight.",
    "That’s enough existence for today.",
    "Logging off before things get weird."
]

def load_config(path: str = "config.yaml") -> dict:
    """Load YAML configuration."""
    p = Path(path)
    if not p.exists():
        print_warning(f"Config not found at {path}, using defaults.")
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def go_dark(listener, transcriber, speaker, llm, reminder_skill, timer_skill):
    """Kill switch: shut everything down, free GPU."""
    print_system("\n[*] Going dark...")

    # Announce
    speaker.speak_sync(random.choice(SIGN_OFFS))

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

    print_system("[OFFLINE] Friday is offline. Press Enter to reboot or Ctrl+C to exit.")


def boot(config: dict):
    """Initialise all components and return them."""
    print_system("[BOOT] Booting components...")

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
        num_predict=llm_cfg.get("num_predict", 200),
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

    # Inject Ollama tool definitions into LLM
    llm.set_tools(get_ollama_tools(skill_registry))

    # Wire up audio ducking: speaker ↔ music skill
    music_skill = skill_registry.get("music")
    if music_skill:
        speaker.set_music_skill(music_skill)

    # ── Orchestrator
    orchestrator = Orchestrator(
        skill_registry=skill_registry,
        llm=llm,
        memory=memory,
        speaker=speaker,
    )

    return listener, transcriber, memory, llm, speaker, skill_registry, orchestrator


def audio_worker(listener, msg_queue):
    while listener._running:
        audio = listener.listen()
        if audio is not None:
            msg_queue.put(("audio", audio))

def text_worker(msg_queue):
    while True:
        try:
            text = sys.stdin.readline()
            if not text:
                break
            
            if text.strip():
                msg_queue.put(("text", text.strip()))
        except (KeyboardInterrupt, EOFError):
            msg_queue.put(("system", "quit"))
            break

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
        
    msg_queue = queue.Queue()
    
    a_thread = threading.Thread(target=audio_worker, args=(listener, msg_queue), daemon=True)
    t_thread = threading.Thread(target=text_worker, args=(msg_queue,), daemon=True)
    a_thread.start()
    t_thread.start()

    print_system("[MIC] Listening... (say a wake word to begin)")
    print_system("[TIP] Type 'quit' to exit\n")

    # Proactive greeting
    print_system("[BOOT] Generating startup greeting (checking reminders and news)...")
    boot_prompt = """
    System has just booted up.

    Your task:
    1. Greet the user briefly and politely (1 sentence max).
    2. Check the "reminder" skill for pending to-dos and summarize them in 1 short sentence.
    3. Use the "web_search" skill to find ONE current interesting news item and summarize it in 1 short sentence.

    Rules:
    - Do NOT invent a name, identity, or location.
    - Do NOT add extra personality or backstory.
    - Keep the total response under 4 sentences.
    - Be concise and neutral-friendly in tone.

    Output format:
    Greeting sentence.

    Reminders: <summary or "No pending reminders.">

    News: <1-line summary of a current news item>
    """
    response, should_speak = orchestrator.handle(boot_prompt, memory.get_history())
    memory.add("assistant", response)
    print_friday(response)
    if should_speak:
        speaker.speak(response)

    try:
        while True:
            try:
                msg_type, payload = msg_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if msg_type == "system" and payload == "quit":
                raise KeyboardInterrupt
                
            if msg_type == "text":
                if payload.lower() in ["quit", "exit", "go dark", "shut down", "kill switch"]:
                    raise KeyboardInterrupt
                
                print_user(payload)
                memory.add("user", payload)
                response, should_speak = orchestrator.handle(payload, memory.get_history())
                memory.add("assistant", response)
                print_friday(response)
                
                if should_speak:
                    speaker.speak(response)
                continue

            if msg_type == "audio":
                result = transcriber.process(payload)
                v_type = result["type"]
                text = result["text"]

                if v_type == "ignored":
                    continue

                if v_type == "go_dark":
                    go_dark(listener, transcriber, speaker, llm,
                            reminder_skill, timer_skill)
                    try:
                        input()
                        print_system("[REBOOT] Rebooting Friday...")
                        memory.clear()
                        return True  # signal to reboot
                    except (KeyboardInterrupt, EOFError):
                        return False

                if v_type == "wake":
                    print_system("[ACTIVE] Yes?")
                    speaker.speak("Yes?")
                    continue

                if v_type == "command":
                    print_user(text)
                    memory.add("user", text)
                    response, should_speak = orchestrator.handle(text, memory.get_history())
                    memory.add("assistant", response)
                    print_friday(response)

                    if should_speak:
                        speaker.speak(response)

    except KeyboardInterrupt:
        print_system("\n[EXIT] Shutting down...")
        go_dark(listener, transcriber, speaker, llm,
                reminder_skill, timer_skill)
        return False


def main():
    console.print(BANNER, style="bold cyan")
    config = load_config()

    reboot = True
    while reboot:
        reboot = main_loop(config)

    print_system("Goodbye!")
    sys.exit(0)


if __name__ == "__main__":
    main()
