"""
Game-wide named constants. All magic numbers that appear in game logic live here.
"""

# ── Battle ────────────────────────────────────────────────────────────────────

# Auto-battle delay between actions (ms)
AUTO_BATTLE_DELAY_MS = 200

# ── Dialogs ───────────────────────────────────────────────────────────────────

# How long a settings message (F2, the speed keys, ...) stays up: a second (not an NES message)
TEMP_TEXT_MS = 1000

# ── Maps ──────────────────────────────────────────────────────────────────────

# Random encounters (which maps have them, and the zone and enemy tables) are in src/encounters.py.

# NES map numbers $0F and up are "dungeons": the Dragonlord's castle sublevels and the caves.
# RETURN and the Wings of the Wyvern don't work in them (or on the castle's bottom floor, CharlockB8).
DUNGEON_MAPS = (
    'CharlockB2', 'CharlockB3', 'CharlockB4', 'CharlockB5', 'CharlockB6', 'CharlockB7Wide', 'CharlockB7Narrow',
    'SwampCave', 'MountainCaveB1', 'MountainCaveB2',
    'GarinsGraveB1', 'GarinsGraveB2', 'GarinsGraveB3', 'GarinsGraveB4',
    'ErdricksCaveB1', 'ErdricksCaveB2',
)

# OUTSIDE destinations from the NES MapEntryTbl, as (map, (row, column)). NES overworld (x, y) is (y + 7, x + 8) here.
_ERDRICKS_CAVE_EXIT = ('Alefgard', (19, 36))
_GARINS_GRAVE_EXIT = ('Garinham', (1, 28))  # OUTSIDE from Garin's Grave leads into Garinham, not the overworld
_MOUNTAIN_CAVE_EXIT = ('Alefgard', (64, 37))
_CHARLOCK_EXIT = ('Alefgard', (55, 56))
OUTSIDE_DESTINATIONS = {
    'ErdricksCaveB1': _ERDRICKS_CAVE_EXIT, 'ErdricksCaveB2': _ERDRICKS_CAVE_EXIT,
    'GarinsGraveB1': _GARINS_GRAVE_EXIT, 'GarinsGraveB2': _GARINS_GRAVE_EXIT,
    'GarinsGraveB3': _GARINS_GRAVE_EXIT, 'GarinsGraveB4': _GARINS_GRAVE_EXIT,
    'MountainCaveB1': _MOUNTAIN_CAVE_EXIT, 'MountainCaveB2': _MOUNTAIN_CAVE_EXIT,
    'SwampCave': ('Alefgard', (51, 112)),  # north entrance
    'CharlockB2': _CHARLOCK_EXIT, 'CharlockB3': _CHARLOCK_EXIT, 'CharlockB4': _CHARLOCK_EXIT,
    'CharlockB5': _CHARLOCK_EXIT, 'CharlockB6': _CHARLOCK_EXIT, 'CharlockB7Wide': _CHARLOCK_EXIT,
    'CharlockB7Narrow': _CHARLOCK_EXIT, 'CharlockB8': _CHARLOCK_EXIT,
}

# RETURN and the Wings of the Wyvern: NES overworld (42, 43), just west of Tantegel Castle
RETURN_DESTINATION = ('Alefgard', (50, 50))

# NES ChkDrop: the Rainbow Drop only works with the hero standing on overworld (65, 49), and ModMapBlock puts the
# bridge one block to the west, on the water at (64, 49) (ChkRnbwBrdg reads that block as BLK_BRIDGE from then on).
RAINBOW_DROP_COORDINATES = (56, 73)
RAINBOW_BRIDGE_COORDINATES = (56, 72)

# NES ChkHarp/HarpRNGLoop: on the overworld the Silver Harp starts a fight with enemy #0-4 or #6 (RandNumUB AND 7,
# rerolling 5 and 7), i.e. each of these six with equal chance
SILVER_HARP_ENEMIES = ('Slime', 'Red Slime', 'Drakee', 'Ghost', 'Magician', 'Scorpion')
# NES CheckTantCursed: a cursed player who steps onto Y=27 of Tantegel's ground floor (two steps in from the gate) is
# told "Cursed one,be gone!" and thrown out to the overworld. NES Tantegel GF (x, y) is (y + 7, x + 7) here.
TANTEGEL_CURSED_ROW = 27 + 7
# Where the cursed player lands: the castle tile on the overworld, NES (43, 43) (MapEntryTbl entry 4, X = $0C)
TANTEGEL_OVERWORLD_EXIT = ('Alefgard', (50, 51))
# NES ThRmStatTbl: Princess Gwaelin's throne room NPC sits at (6, 3), facing down, next to King Lorik at (3, 3).
# The throne room here is offset by (+6 rows, +10 columns), so King Lorik is at (9, 13) and Gwaelin at (9, 16).
GWAELIN_THRONE_ROOM_COORDINATES = (9, 16)
# Where she waits in the Swamp Cave until she's rescued
GWAELIN_SWAMP_CAVE_COORDINATES = (24, 9)

# NES InvListTbl: if the inventory is full when King Lorik gives Gwaelin's Love, the first of these the hero has is
# taken to make room. If none of them is there, Gwaelin's Love isn't given.
GWAELINS_LOVE_REPLACEABLE_ITEMS = (
    'Torch', "Dragon's Scale", "Fighter's Ring", 'Fairy Water', 'Wings', 'Cursed Belt', 'Staff of Rain')

# NES ChangeMaps with X = $12 after the final boss falls: the overworld at the Dragonlord's castle entrance
DRAGONLORD_DEFEATED_DESTINATION = _CHARLOCK_EXIT

# NES CheckForTriggers: after the Dragonlord's defeat, stepping on Tantegel ground floor (10, 8) or (11, 8), just below
# King Lorik, starts the ending. NES (x, y) on the ground floor is (y + 7, x + 7) here.
ENDING_TRIGGER_COORDINATES = ((15, 17), (15, 18))
ENDING_GWAELIN_STAIRS = (14, 14)  # NES GwaelinXPos $C7 / GwaelinYPos $27: (7, 7), the throne room stairs
ENDING_GWAELIN_BESIDE_KING = (14, 17)  # NES $CA / $47: (10, 7), next to King Lorik at (11, 7)

# NES LVL_30: the highest level
MAX_LEVEL = 30

# NES RepelTimer: REPEL sets it to 255 and Fairy Water to 254; it drops by 2 per step (127 steps either way)
REPEL_SPELL_TIMER = 255
FAIRY_WATER_TIMER = 254

# ── Sprites ───────────────────────────────────────────────────────────────────

# NES InitMapData (ChkLeftThRoom, Bank00): once F_LEFT_THROOM is set, entering the throne room removes its door
# (DoorXPos+14 = 4, DoorYPos+14 = 7) along with its 3 treasure chests. NES throne room (x, y) is (y + 6, x + 10) here.
THRONE_ROOM_DOOR_COORDINATES = (7 + 6, 4 + 10)
# The throne room tile in front of King Lorik, where a new quest starts and a dead hero wakes up
THRONE_ROOM_START_COORDINATES = (10, 13)
