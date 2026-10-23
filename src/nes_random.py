"""Chances the way the NES rolls them: one random byte (0-255) and a look at some of its bits.

The NES (UpdateRandNum, Bank03) keeps a 16-bit random number and most rolls read its upper byte, RandNumUB, then
test bits of it: ``AND #$01`` for 50%, ``AND #$1F`` + ``BEQ`` for 1 in 32, and so on. These helpers say what the roll
means; the bit tests stay inside them, and each call reads one byte from ``random.randint(0, 255)`` exactly as the
inline expressions they replace did (so seeded runs and the tests' ``random.randint`` patches see the same calls).
"""
import random


def random_byte() -> int:
    """A random 0-255 (NES RandNumUB)."""
    return random.randint(0, 255)


def coin_flip() -> bool:
    """50%: bit 0 of a random byte is set (AND #$01)."""
    return bool(random_byte() & 0x01)


def one_in(chances: int) -> bool:
    """A 1 in ``chances`` roll, ``chances`` being a power of two up to 256: the low bits of a random byte are all 0
    (e.g. AND #$1F, BEQ for 1 in 32)."""
    return random_byte() & (chances - 1) == 0
