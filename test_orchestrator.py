"""Quick orchestrator smoke test."""
from brain.orchestrator import Orchestrator
from skills.clock import ClockSkill
from skills.dice import DiceSkill

reg = {"clock": ClockSkill(), "dice": DiceSkill()}
o = Orchestrator(reg)

# Test ACTION parsing
r1 = o.handle('ACTION::clock::{"query": "time"}')
print(f"Clock: {r1}")

r2 = o.handle('ACTION::dice::{"type": "d20"}')
print(f"Dice: {r2}")

# Test plain text passthrough
r3 = o.handle("Just a plain text reply.")
print(f"Plain: {r3}")

print("\norchestrator OK")
