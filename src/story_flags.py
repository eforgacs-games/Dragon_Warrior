"""
Story progress that changes the world once it's reached, kept in one place so that saving can persist it.

Mirrors the NES StoryFlags and PlayerFlags bits (see Dragon_Warrior_Defines.asm in the nmikstas disassembly).
"""

from dataclasses import dataclass


@dataclass
class StoryFlags:
    # NES F_DGNLRD_DEAD: set as the Ball of Light is found after beating the Dragonlord's final form. From then on there
    # are no random fights or swamp/barrier damage, every NPC has victory dialog, and Tantegel waits for the hero.
    dragonlord_defeated: bool = False
    # NES F_RTN_GWAELIN: Princess Gwaelin was carried back to King Lorik.
    gwaelin_returned: bool = False
