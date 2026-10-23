"""Autosave (AUTOSAVE in the options overlay): a save state written now and then, so a crash or a closed laptop never
costs much progress. Not NES.

The NES saves only with King Lorik, into an adventure log (src/save_file.py), and that is unchanged: the autosave is a
separate slot, autosave.json in the save folder, holding a save state snapshot (src/save_state.py take_snapshot) in
the save state file format. It's written, with AUTOSAVE ON, between two map frames (Game.map_frame):
- on entering a town or a castle from the overworld (AUTOSAVE_MAPS), once the new map is up;
- every AUTOSAVE_INTERVAL_MS of real time on the map, so a long trip in a dungeon or on the overworld is kept too.
The interval is real time, not game time, so it's the same at any game speed (keys 1 to 5); it starts again after each
autosave.

Nothing is said on screen: the autosave never interrupts play. The title menu shows CONTINUE AUTOSAVE as its last
entry when there's an autosave (src/title_menu.py), which puts the game back as it was when it was written, as loading
a save state does. Continuing from it doesn't change the adventure logs; saving with King Lorik still writes to the
hero's log.
"""
import os
from typing import Any

from pygame.time import get_ticks

from src.options_screen import DEFAULT_AUTOSAVE
from src.save_state import read_snapshot, take_snapshot, write_snapshot

AUTOSAVE_FILE_NAME = 'autosave.json'
# Every 3 minutes of real time on the map
AUTOSAVE_INTERVAL_MS = 3 * 60 * 1000
# The towns and castles whose entry from the overworld writes an autosave (not Hauksness, a ruin full of monsters, or
# Charlock, the Dragonlord's)
AUTOSAVE_MAPS = ('TantegelCourtyard', 'Brecconary', 'Garinham', 'Kol', 'Rimuldar', 'Cantlin')
OVERWORLD = 'Alefgard'


def autosave_path(save_dir: str) -> str:
    return os.path.join(save_dir, AUTOSAVE_FILE_NAME)


def has_autosave(save_dir: str) -> bool:
    return os.path.exists(autosave_path(save_dir))


def read_autosave(save_dir: str) -> dict[str, Any] | None:
    """The autosave's snapshot, or None if there is none. Raises StateError if it can't be read or is from another
    format version."""
    return read_snapshot(autosave_path(save_dir))


class Autosave:
    """When to write the autosave (see the module docstring); Game.map_frame calls frame() at the end of each frame."""

    def __init__(self, game: Any):
        self.game = game
        self.last_written = get_ticks()
        self.last_map: str | None = None
        self.entered_town = False

    @property
    def enabled(self) -> bool:
        return bool(self.game.config.get('AUTOSAVE', DEFAULT_AUTOSAVE))

    def frame(self) -> None:
        """Write the autosave if it's due (a town or castle entered from the overworld, or the interval gone by) and
        AUTOSAVE is ON. A due autosave waits for the hero to finish the step under way, so it's always written with
        the hero on a tile, as a save state is."""
        current = self.game.current_map.identifier
        if self.last_map == OVERWORLD and current in AUTOSAVE_MAPS:
            self.entered_town = True
        self.last_map = current
        if not self.enabled:
            self.entered_town = False
            return
        if self.game.player.is_moving:
            return
        if self.entered_town or get_ticks() - self.last_written >= AUTOSAVE_INTERVAL_MS:
            self.write()

    def restart(self) -> None:
        """Start the interval again, from now."""
        self.last_written = get_ticks()

    def write(self) -> None:
        """Write the autosave now; the interval starts again."""
        try:
            write_snapshot(autosave_path(self.game.directories.save_dir), take_snapshot(self.game))
        except OSError as error:
            # A full disk or a read-only save folder: play goes on, and the next autosave tries again
            print(f"Autosave failed: {error}")
        self.last_written = get_ticks()
        self.entered_town = False
