"""
Game-wide named constants. All magic numbers that appear in game logic live here.
"""

# ── Battle ────────────────────────────────────────────────────────────────────

# Probability index used with randint(0, EXCELLENT_MOVE_THRESHOLD)
EXCELLENT_MOVE_PROBABILITY = 0
EXCELLENT_MOVE_THRESHOLD = 31

# Probability that a near-miss attack plays the "miss" sound instead of dealing 0 damage
MISS_SFX_PROBABILITY = 0.5

# Minimum damage dealt before the miss-sound check applies
MIN_DAMAGE = 1

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

# ── Sprites ───────────────────────────────────────────────────────────────────

# How many frames to wait before advancing the animation frame
ANIMATION_FRAME_DELAY = 2

# Number of update ticks per animation cycle check
ANIMATION_CYCLE_TICKS = 15

# Maximum animation frame index (0-based, so 2 frames total)
ANIMATION_MAX_FRAME = 1
