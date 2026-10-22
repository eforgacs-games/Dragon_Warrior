"""Random encounters, as the NES does them after every step (Bank03 CheckBlockDmg -> ChkFight... -> DoRandomFight).

1. The block the player has just stepped onto sets the chance of a fight (fight_mask): the fight starts when
   RandNumUB AND mask is 0.
2. DoRandomFight picks a row of EnemyGroupsTbl: from OvrWrldEnGrid on the overworld, or per map in the dungeons
   (encounter_group). Maps without a row never start random fights.
3. Zone 0 of the overworld (around Tantegel) gets one more roll to skip the fight (passes_zone_zero_check).
4. GetEnemyInRow picks one of the row's five slots (pick_enemy).
"""
import random
from typing import Sequence

# NES EnemyGroupsTbl (Bank03): five slots per row. A repeated enemy is that much more likely, since each slot is
# equally likely. Rows $00-$0D are the overworld zones (OvrWrldEnGrid), rows $0E-$13 are for the dungeons.
ENEMY_GROUPS: tuple[tuple[str, str, str, str, str], ...] = (
    ('Slime', 'Red Slime', 'Slime', 'Red Slime', 'Slime'),  # $00
    ('Red Slime', 'Slime', 'Red Slime', 'Drakee', 'Red Slime'),  # $01
    ('Slime', 'Ghost', 'Drakee', 'Ghost', 'Red Slime'),  # $02
    ('Red Slime', 'Red Slime', 'Drakee', 'Ghost', 'Magician'),  # $03
    ('Ghost', 'Magician', 'Magidrakee', 'Magidrakee', 'Scorpion'),  # $04
    ('Ghost', 'Magician', 'Magidrakee', 'Scorpion', 'Skeleton'),  # $05
    ('Magidrakee', 'Scorpion', 'Skeleton', 'Warlock', 'Wolf'),  # $06
    ('Skeleton', 'Warlock', 'Metal Scorpion', 'Wolf', 'Wolf'),  # $07
    ('Metal Scorpion', 'Wraith', 'Wolflord', 'Wolflord', 'Goldman'),  # $08
    ('Wraith', 'Wyvern', 'Wolflord', 'Wyvern', 'Goldman'),  # $09
    ('Wyvern', 'Rogue Scorpion', 'Wraith Knight', 'Knight', 'Demon Knight'),  # $0A
    ('Wraith Knight', 'Knight', 'Magiwyvern', 'Demon Knight', 'Metal Slime'),  # $0B
    ('Knight', 'Magiwyvern', 'Demon Knight', 'Werewolf', 'Starwyvern'),  # $0C
    ('Werewolf', 'Green Dragon', 'Starwyvern', 'Starwyvern', 'Wizard'),  # $0D
    ('Poltergeist', 'Droll', 'Drakeema', 'Skeleton', 'Warlock'),  # $0E
    ('Specter', 'Wolflord', 'Druinlord', 'Drollmagi', 'Wraith Knight'),  # $0F
    ('Werewolf', 'Green Dragon', 'Starwyvern', 'Wizard', 'Axe Knight'),  # $10
    ('Wizard', 'Axe Knight', 'Blue Dragon', 'Blue Dragon', 'Stoneman'),  # $11
    ('Wizard', 'Stoneman', 'Armored Knight', 'Armored Knight', 'Red Dragon'),  # $12
    ('Ghost', 'Magician', 'Scorpion', 'Druin', 'Druin'),  # $13
)

# NES OvrWrldEnGrid (Bank03): the overworld is an 8x8 grid of zones, each 15x15 blocks (DoRandomFight divides
# CharXPos and CharYPos by 15 with ByteDivide). Each entry is a row of ENEMY_GROUPS. Indexed [zone_y][zone_x].
OVERWORLD_ZONE_SIZE = 15
OVERWORLD_ZONE_GRID: tuple[tuple[int, ...], ...] = (
    (0x3, 0x3, 0x2, 0x2, 0x3, 0x5, 0x4, 0x5),
    (0x3, 0x2, 0x1, 0x2, 0x3, 0x3, 0x4, 0x5),
    (0x4, 0x1, 0x0, 0x0, 0x2, 0x3, 0x4, 0x5),
    (0x5, 0x1, 0x1, 0xC, 0x6, 0x6, 0x6, 0x6),
    (0x5, 0x5, 0x4, 0xC, 0x9, 0x7, 0x7, 0x7),
    (0xA, 0x9, 0x8, 0xC, 0xC, 0xC, 0x8, 0x7),
    (0xA, 0xA, 0xB, 0xC, 0xD, 0xD, 0x9, 0x8),
    (0xB, 0xB, 0xC, 0xD, 0xD, 0xC, 0x9, 0x9),
)

# Rows of ENEMY_GROUPS for every map other than the overworld that has random fights. DoRandomFight:
# ChkDungeonFights (DL castle GF -> $10), ChkHauksnessFight ($0D), ChkDLCastleFight (DL castle BF -> $12), then
# CaveEnIndexTbl for the dungeon maps $0F-$1B. ChkErdrickFight: Erdrick's Cave (maps $1C and up) has none, and towns,
# castles and the shrines (MapType isn't MAP_DUNGEON) have none either.
DUNGEON_ENEMY_GROUPS: dict[str, int] = {
    'CharlockB1': 0x10,  # MAP_DLCSTL_GF
    'Hauksness': 0x0D,  # MAP_HAUKSNESS
    'CharlockB8': 0x12,  # MAP_DLCSTL_BF
    # CaveEnIndexTbl: $10, $11, $11, $11, $12, $12, $13, $13, $0E, $0E, $07, $0F, $0F
    'CharlockB2': 0x10,  # MAP_DLCSTL_SL1
    'CharlockB3': 0x11,  # MAP_DLCSTL_SL2
    'CharlockB4': 0x11,  # MAP_DLCSTL_SL3
    'CharlockB5': 0x11,  # MAP_DLCSTL_SL4
    'CharlockB6': 0x12,  # MAP_DLCSTL_SL5
    'CharlockB7Wide': 0x12,  # MAP_DLCSTL_SL6 (lower corridor)
    'CharlockB7Narrow': 0x12,  # MAP_DLCSTL_SL6 (upper corridor)
    'SwampCave': 0x13,  # MAP_SWAMPCAVE
    'MountainCaveB1': 0x13,  # MAP_RCKMTN_B1
    'MountainCaveB2': 0x0E,  # MAP_RCKMTN_B2
    'GarinsGraveB1': 0x0E,  # MAP_CVGAR_B1
    'GarinsGraveB2': 0x07,  # MAP_CVGAR_B2
    'GarinsGraveB3': 0x0F,  # MAP_CVGAR_B3
    'GarinsGraveB4': 0x0F,  # MAP_CVGAR_B4
}

# (column, row) offsets of this project's layouts from the NES map coordinates (from MapEntryTbl/MapTargetTbl and the
# map docstrings). The overworld zone needs the NES position, and the grass-type fight chance its parity.
NES_COORDINATE_OFFSETS: dict[str, tuple[int, int]] = {
    'Alefgard': (8, 7),
    'CharlockB1': (7, 6),
    'Hauksness': (9, 8),
    'CharlockB8': (6, 4),
    'CharlockB2': (3, 3),
    'CharlockB3': (3, 3),
    'CharlockB4': (3, 3),
    'CharlockB5': (3, 3),
    'CharlockB6': (3, 3),
    'CharlockB7Wide': (3, -1),
    'CharlockB7Narrow': (3, 3),
    'SwampCave': (4, 6),
    'MountainCaveB1': (1, 1),
    'MountainCaveB2': (1, 1),
    'GarinsGraveB1': (1, 1),
    'GarinsGraveB2': (1, 1),
    'GarinsGraveB3': (1, 1),
    'GarinsGraveB4': (1, 1),
}

# CheckBlockDmg: BLK_TOWN, BLK_CAVE and BLK_CASTLE go to CalcNextMap instead of the fight checks. (Bridges, BLK_BRIDGE,
# and stairs, BLK_STAIR_UP/BLK_STAIR_DN, do get the fight check.) GRASS_STAIR_DOWN is this project's tile for the
# overworld shrine entrances, which are cave blocks on the NES.
MAP_CHANGE_TILES = frozenset({'TOWN', 'CASTLE', 'CAVE', 'GRASS_STAIR_DOWN'})


def nes_coordinates(map_identifier: str, column: int, row: int) -> tuple[int, int]:
    """The NES CharXPos/CharYPos for a position on one of this project's layouts."""
    column_offset, row_offset = NES_COORDINATE_OFFSETS.get(map_identifier, (0, 0))
    return column - column_offset, row - row_offset


def overworld_zone(column: int, row: int) -> tuple[int, int]:
    """DoRandomFight: the (zone_x, zone_y) of OvrWrldEnGrid for a position on the Alefgard layout."""
    x, y = nes_coordinates('Alefgard', column, row)
    return min(max(x, 0) // OVERWORLD_ZONE_SIZE, 7), min(max(y, 0) // OVERWORLD_ZONE_SIZE, 7)


def encounter_group(map_identifier: str, column: int, row: int) -> int | None:
    """The row of ENEMY_GROUPS fights come from here, or None on a map with no random fights."""
    if map_identifier == 'Alefgard':
        zone_x, zone_y = overworld_zone(column, row)
        return OVERWORLD_ZONE_GRID[zone_y][zone_x]
    return DUNGEON_ENEMY_GROUPS.get(map_identifier)


def fight_mask(tile: str | None, nes_x: int, nes_y: int) -> int | None:
    """CheckBlockDmg: a fight starts when RandNumUB AND this mask is 0, or never (None) on a map-changing block."""
    if tile in MAP_CHANGE_TILES:
        return None
    if tile in ('SAND', 'HILLS'):
        return 0x07  # ChkSandFight: 1 in 8
    if tile in ('MARSH', 'TREES', 'BRICK', 'BARRIER'):
        return 0x0F  # ChkFight (swamp) / ChkRandomFight (trees, bricks, force field): 1 in 16
    # ChkFight6, for grass and every other block (bridges, stairs, chests...): HighFightChance (1 in 32) when X and Y
    # are both even or both odd, NormFightChance (1 in 16) otherwise.
    return 0x1F if (nes_x + nes_y) % 2 == 0 else 0x0F


def step_starts_fight(map_identifier: str, tile: str | None, column: int, row: int) -> bool:
    """The per-step roll: does stepping onto this block start a fight?"""
    mask = fight_mask(tile, *nes_coordinates(map_identifier, column, row))
    return mask is not None and random.randint(0, mask) == 0


def passes_zone_zero_check(tile: str | None) -> bool:
    """DoRandomFight, zone 0 only: one more roll that lets the fight go ahead 1 time in 4 on hills
    (HighFightModifier, RandNumUB AND 3) and 1 time in 2 elsewhere (NormFightModifier, RandNumUB AND 1)."""
    return random.randint(0, 3 if tile == 'HILLS' else 1) == 0


def pick_enemy(group: Sequence[str]) -> str:
    """GetEnemyInRow: roll 0-7 (RandNumUB AND 7) and roll again until the slot is in the row (0-4 for a full row)."""
    while (slot := random.randint(0, 7)) >= len(group):
        pass
    return group[slot]


def roll_encounter(map_identifier: str, tile: str | None, column: int, row: int) -> tuple[str, ...] | None:
    """One step's encounter check, up to choosing the enemy row: the row to fight from, or None for no fight."""
    group = encounter_group(map_identifier, column, row)
    if group is None or not step_starts_fight(map_identifier, tile, column, row):
        return None
    if group == 0 and not passes_zone_zero_check(tile):
        return None
    return ENEMY_GROUPS[group]
