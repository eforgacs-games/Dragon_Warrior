"""
Game-wide named constants. All magic numbers that appear in game logic live here.
"""

# ── Battle ────────────────────────────────────────────────────────────────────

# Probability index used with randint(0, EXCELLENT_MOVE_THRESHOLD)
EXCELLENT_MOVE_PROBABILITY = 0
EXCELLENT_MOVE_THRESHOLD = 31

# Fraction of player max HP below which the text color turns red
LOW_HP_THRESHOLD = 0.125

# Probability that a dominant enemy attempts to flee
ENEMY_FLEE_PROBABILITY = 0.25

# Auto-battle delay between actions (ms)
AUTO_BATTLE_DELAY_MS = 200

# Arrow blink timer interval (ms)
ARROW_BLINK_INTERVAL_MS = 530

# ── Battle menu window position (tile units): x, y, width, height ─────────────
BATTLE_MENU_X = 6
BATTLE_MENU_Y = 1
BATTLE_MENU_WIDTH = 8
BATTLE_MENU_HEIGHT = 3

# ── Maps ──────────────────────────────────────────────────────────────────────

# Maps that contain random enemy encounters
MAPS_WITH_ENEMIES = (
    'Alefgard',
    'Hauksness',
    'CharlockB2', 'CharlockB3', 'CharlockB4', 'CharlockB5',
    'CharlockB6', 'CharlockB7Wide', 'CharlockB7Narrow', 'CharlockB8',
    'SwampCave', 'MountainCaveB1',
    'GarinsGraveB1', 'GarinsGraveB2', 'GarinsGraveB3', 'GarinsGraveB4',
)

# Fixed zone keys for dungeons (negative tuples avoid collision with Alefgard grid zones)
DUNGEON_ZONE_MAP = {
    'Hauksness':       (3, 7),    # forced dark_blue zone
    'SwampCave':       (-1, -1),
    'GarinsGraveB1':   (-2, -2),
    'GarinsGraveB2':   (-3, -3),
    'GarinsGraveB3':   (-4, -4),
    'GarinsGraveB4':   (-5, -5),
    'CharlockB1':      (-6, -6),
    'CharlockB2':      (-7, -7),
    'CharlockB3':      (-8, -8),
    'CharlockB4':      (-9, -9),
    'CharlockB5':      (-10, -10),
    'CharlockB6':      (-11, -11),
    'CharlockB7Wide':  (-12, -12),
    'CharlockB7Narrow':(-13, -13),
    'CharlockB8':      (-14, -14),
    'MountainCaveB1':  (-15, -15),
}

# Zone that uses the near-Tantegel fight-rate modifier
TANTEGEL_ZONE = (3, 2)

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
_GARINS_GRAVE_EXIT = ('Garinham', (0, 28))  # OUTSIDE from Garin's Grave leads into Garinham, not the overworld
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

# NES RepelTimer: REPEL sets it to 255 and Fairy Water to 254; it drops by 2 per step (127 steps either way)
REPEL_SPELL_TIMER = 255
FAIRY_WATER_TIMER = 254

# ── Sprites ───────────────────────────────────────────────────────────────────

# How many frames to wait before advancing the animation frame
ANIMATION_FRAME_DELAY = 2

# Number of update ticks per animation cycle check
ANIMATION_CYCLE_TICKS = 15

# Maximum animation frame index (0-based, so 2 frames total)
ANIMATION_MAX_FRAME = 1
