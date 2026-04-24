"""
skills/volume.py — System volume control via pycaw (Windows).
"""

from skills.base import BaseSkill


class VolumeSkill(BaseSkill):
    name = "volume"
    description = "Control system volume: set, up, down, mute, unmute, get."
    schema = {
        "command": {"type": "string", "enum": ["set", "up", "down", "mute", "unmute", "get"]},
        "level": {"type": "integer", "description": "Volume level 0-100 (for 'set')."},
        "step": {"type": "integer", "description": "Step amount (for 'up'/'down'). Default: 10."}
    }

    def __init__(self):
        self._vol = None
        self._init_pycaw()

    def _init_pycaw(self):
        try:
            from pycaw.pycaw import AudioUtilities
            device = AudioUtilities.GetSpeakers()
            self._vol = device.EndpointVolume
        except Exception as e:
            print(f"  [VOLUME] pycaw init failed: {e}")

    def _get_pct(self) -> int:
        if not self._vol:
            return -1
        cur = self._vol.GetMasterVolumeLevelScalar()
        return int(round(cur * 100))

    def _set_pct(self, pct: int):
        if not self._vol:
            return
        pct = max(0, min(100, pct))
        self._vol.SetMasterVolumeLevelScalar(pct / 100.0, None)

    def execute(self, params: dict) -> str:
        if not self._vol:
            return "Volume control unavailable (pycaw not initialised)."
        cmd = params.get("command", "get")

        if cmd == "get":
            return f"Volume is at {self._get_pct()}%."
        elif cmd == "set":
            level = params.get("level", 50)
            self._set_pct(level)
            return f"Volume set to {level}%."
        elif cmd == "up":
            step = params.get("step", 10)
            new = min(100, self._get_pct() + step)
            self._set_pct(new)
            return f"Volume up to {new}%."
        elif cmd == "down":
            step = params.get("step", 10)
            new = max(0, self._get_pct() - step)
            self._set_pct(new)
            return f"Volume down to {new}%."
        elif cmd == "mute":
            self._vol.SetMute(1, None)
            return "Muted."
        elif cmd == "unmute":
            self._vol.SetMute(0, None)
            return "Unmuted."
        return f"Unknown volume command: {cmd}"
