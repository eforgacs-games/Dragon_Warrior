"""
The NPC tables. Each map with NPCs has one (DragonWarriorMap.npc_table, src/maps.py) in the order of its NES tables
(Bank00): the mobile NPC table (TantMobTbl, KolMobTbl, ...), whose order is the order of the mobile NPC slots
(src/npc_schedule.py), then the static one (TantStatTbl, KolStatTbl, ...).

Each NES entry is three bytes, NNNXXXXX _DDYYYYY CCCCCCCC: the graphic, X, the direction it faces, Y and the dialog
control byte. CheckTalk and DoDialog (Bank03) decide what an NPC says from the dialog byte alone, so the byte is what
DialogLookup (data/text/dialog_lookup_table.py) looks the NPC's dialog up by.
"""
from dataclasses import dataclass

from src.direction import Direction

# Gwaelin in the Swamp Cave isn't an NES NPC: she's block $6 (BLK_PRINCESS) of SwampCaveDat, and DoTalkResults
# (Bank03) starts her rescue when the hero talks to that block. This stands in for her dialog byte.
GWAELIN_RESCUE = 'BLK_PRINCESS'
# The dialog byte of Brecconary's guard who searched for Gwaelin (ChkPrncsDialog3), who says "...." once the Dragonlord
# is dead (TantEndDialog)
SEARCHED_FOR_GWAELIN = 0x64


@dataclass(frozen=True, slots=True)
class NPC:
    """One NPC table entry.

    name: the NPC's identifier here (Game.characters etc.): its sprite type (MAN, WISE_MAN, ...), with a number added
        for the second and later NPCs of that type on the map.
    x, y: its NES position. It's at layout (y, x) + the map's nes_origin (DragonWarriorMap.npc_position).
    dialog: the NES dialog control byte (or GWAELIN_RESCUE).
    facing: the direction it faces when the map is loaded (the DD bits).
    mobile: whether it's from the mobile NPC table, i.e. roams.
    """
    name: str
    x: int
    y: int
    dialog: int | str
    facing: Direction = Direction.DOWN
    mobile: bool = False

    @property
    def sprite(self) -> str:
        """The sprite type: the name without its number (WISE_MAN_2 is a WISE_MAN)."""
        sprite, _, number = self.name.rpartition('_')
        return sprite if number.isdigit() else self.name
