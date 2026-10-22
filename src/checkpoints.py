"""
Named checkpoints for playtesting: one save file per chapter of the critical path, kept in data/checkpoints/.

Each checkpoint is an ordinary save file (the format CommandMenu.save writes) and is loaded with Game.load_game, so it
follows the real load path. Two things differ from a save made in the game:
- The position isn't always beside King Lorik. load_game already starts wherever the save says (CurrentMap, PlayerRow
  and PlayerColumn), unlike the NES, which always starts in the throne room.
- The optional "Facing" key ("UP", "DOWN", "LEFT" or "RIGHT") turns the hero to face an NPC. Saves don't keep the
  direction, so Game.load_checkpoint applies it after load_game.

Load one with `python src/game.py --dev --checkpoint rainbow_bridge` (or set "CHECKPOINT" in a config). Saving with
King Lorik in a game started from a checkpoint writes to CHECKPOINT_SAVE_DIR instead of the real slots in src/saves/.
"""
import json
import tempfile
from os.path import dirname, join, realpath

CHECKPOINTS_DIR = join(dirname(dirname(realpath(__file__))), 'data', 'checkpoints')

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

# Where saves made in a game started from a checkpoint go, so the real save slots stay as they are
CHECKPOINT_SAVE_DIR = join(tempfile.gettempdir(), 'dragon_warrior_checkpoint_saves')


def checkpoint_path(name: str) -> str:
    if name not in CHECKPOINT_NAMES:
        raise ValueError(f"Unknown checkpoint {name!r}. Checkpoints: {', '.join(CHECKPOINT_NAMES)}")
    return join(CHECKPOINTS_DIR, f'{name}.json')


def read_checkpoint(name: str) -> dict:
    with open(checkpoint_path(name)) as checkpoint_file:
        return json.load(checkpoint_file)
