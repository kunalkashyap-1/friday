"""
skills/dice.py — Dice, coin flip, and random number generation.
"""

import random
from skills.base import BaseSkill


class DiceSkill(BaseSkill):
    name = "dice"
    description = "Roll dice, flip a coin, or pick a random number."
    schema = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["d4", "d6", "d8", "d10", "d12", "d20", "d100", "coin", "number"],
                "description": "Type of roll. Use 'dN' for N-sided die, 'coin' for heads/tails, 'number' for a range.",
            },
            "min": {
                "type": "integer",
                "description": "Minimum value (only for type='number'). Default: 1.",
            },
            "max": {
                "type": "integer",
                "description": "Maximum value (only for type='number'). Default: 100.",
            },
            "count": {
                "type": "integer",
                "description": "Number of dice to roll. Default: 1.",
            },
        },
        "required": ["type"],
    }

    def execute(self, params: dict) -> str:
        roll_type = params.get("type", "d20").lower()
        count = max(1, params.get("count", 1))

        # Coin flip
        if roll_type == "coin":
            results = [random.choice(["Heads", "Tails"]) for _ in range(count)]
            if count == 1:
                return f"Coin flip: {results[0]}!"
            return f"Coin flips: {', '.join(results)}."

        # Random number from range
        if roll_type == "number":
            lo = params.get("min", 1)
            hi = params.get("max", 100)
            results = [random.randint(lo, hi) for _ in range(count)]
            if count == 1:
                return f"Random number ({lo}–{hi}): {results[0]}."
            return f"Random numbers ({lo}–{hi}): {', '.join(map(str, results))}."

        # Dice roll (d4, d6, d8, d10, d12, d20, d100, etc.)
        if roll_type.startswith("d") and roll_type[1:].isdigit():
            sides = int(roll_type[1:])
            results = [random.randint(1, sides) for _ in range(count)]
            if count == 1:
                return f"[dice] {roll_type} roll: {results[0]}!"
            total = sum(results)
            return f"[dice] {count}x {roll_type}: {', '.join(map(str, results))} (total: {total})."

        return f"Don't know how to roll a '{roll_type}'."
