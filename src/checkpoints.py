"""
Named checkpoints for playtesting: one save file per chapter of the critical path, kept in data/checkpoints/.

Each checkpoint is an ordinary save file (the format CommandMenu.save writes) and is loaded with Game.load_game, so it
follows the real load path. Two things differ from a save made in the game:
- The position isn't always beside King Lorik. load_game already starts wherever the save says (CurrentMap, PlayerRow
  and PlayerColumn), unlike the NES, which always starts in the throne room.
- Every checkpoint names the hero CHECKPOINT_HERO_NAME, and Game.load_checkpoint swaps in LOCALIZED_HERO_NAMES for
  the game's language. Real saves keep the name the player typed. See CHECKPOINT_HERO_NAME for why these names.
- The optional "Facing" key ("UP", "DOWN", "LEFT" or "RIGHT") turns the hero to face an NPC. Saves don't keep the
  direction, so Game.load_checkpoint passes it to load_game.

Load one with `python src/game.py --dev --checkpoint rainbow_bridge` (or set "CHECKPOINT" in a config). Saving with
King Lorik in a game started from a checkpoint writes to CHECKPOINT_SAVE_DIR instead of the real slots in src/saves/.
"""
import json
import tempfile
from os.path import join

from src.paths import data_path

CHECKPOINTS_DIR = data_path('checkpoints')

# In story order. Each one is data/checkpoints/<name>.json.
CHECKPOINT_NAMES = (
    'throne_room',  # 1. a fresh start in the throne room
    'garins_grave',  # 2. Magic Keys and the Stones of Sunlight in hand, at the top of the stairs to Garin's Grave
    'swamp_cave',  # 3. just outside the Swamp Cave, levelled enough to rescue Gwaelin
    'rainbow_drop_shrine',  # 4. the Staff of Rain, the Stones and Erdrick's Token, beside the Rainbow Drop shrine's sage
    'rainbow_bridge',  # 5. holding the Rainbow Drop on the tile where it builds the bridge
    'charlock_throne',  # 6. on Charlock's ground floor, at the Dragonlord's throne
    'dragonlord',  # 7. on B8, facing the Dragonlord, with endgame gear
    'ending_gwaelin_returned',  # 8. the Dragonlord is dead and Gwaelin was returned; outside Tantegel
    'ending_carrying_gwaelin',  # 9. the Dragonlord is dead and Gwaelin is still carried; outside Tantegel
)

FACING_KEY = 'Facing'

# The hero's name in every checkpoint, and what it becomes in each other language (config LANGUAGE). Not Erdrick:
# that's the hero's ancestor (로토 in Korean). The names are picked for the strongest stats, so playtests go quickly:
# NES LoadStats sums the first four name tiles, and a sum ending in $D cuts agility and MP but keeps full strength and
# HP, with the largest bonus (+3). "Arthur" sums to $6D. 검객 (swordsman) sums to $5D with this game's Korean mapping
# (low byte of each code point); 용사 would sum to $15, which cuts agility and MP for only +1.
CHECKPOINT_HERO_NAME = 'Arthur'
LOCALIZED_HERO_NAMES = {'Korean': '검객'}

# Where saves made in a game started from a checkpoint go, so the real save slots stay as they are
CHECKPOINT_SAVE_DIR = join(tempfile.gettempdir(), 'dragon_warrior_checkpoint_saves')


def checkpoint_path(name: str) -> str:
    if name not in CHECKPOINT_NAMES:
        raise ValueError(f"Unknown checkpoint {name!r}. Checkpoints: {', '.join(CHECKPOINT_NAMES)}")
    return join(CHECKPOINTS_DIR, f'{name}.json')


def read_checkpoint(name: str) -> dict:
    with open(checkpoint_path(name)) as checkpoint_file:
        return json.load(checkpoint_file)


def checkpoint_hero_name(name: str, language: str) -> str:
    """The checkpoint's hero name in the game's language. Only the generic CHECKPOINT_HERO_NAME is translated."""
    if name != CHECKPOINT_HERO_NAME:
        return name
    return LOCALIZED_HERO_NAMES.get(language, name)
