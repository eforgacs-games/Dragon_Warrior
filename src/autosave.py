"""Autosave (AUTOSAVE in the options overlay): a save state written now and then, so a crash or a closed laptop never
costs much progress. Not NES.

The NES saves only with King Lorik, into an adventure log (src/save_file.py), and that is unchanged: the autosave is a
separate slot, autosave.json in the save folder, holding a save state snapshot (src/save_state.py take_snapshot) in
the save state file format. It's written, with AUTOSAVE ON, between two map frames (Game.map_frame):
- on entering a town or a castle from the overworld (AUTOSAVE_MAPS), once the new map is up;
- every AUTOSAVE_INTERVAL_MS of real time on the map, so a long trip in a dungeon or on the overworld is kept too.
The interval is real time, not game time, so it's the same at any game speed (keys 1 to 5); it starts again after each
autosave. Like a save state, it's never written while the map is held (MovementController.map_held: the game paused,
a window open or about to open, the light growing), and the time the map is held doesn't count toward the interval:
a game left paused overnight isn't autosaved, and gets no autosave the moment it's unpaused either.

Nothing is said on screen: the autosave never interrupts play. The title menu shows CONTINUE AUTOSAVE as its last
entry when there's an autosave (src/title_menu.py), which puts the game back as it was when it was written, as loading
a save state does. Continuing from it doesn't change the adventure logs; saving with King Lorik still writes to the
hero's log.

There's one autosave, whoever's adventure it is: it's where the last game played was, whichever log it's from. It can
never be saved over another hero's log: the snapshot keeps the hero's adventure log, CommandMenu.save checks that the
log still holds that hero, and erasing a log (or copying another into it) deletes the autosave and the save states
of the hero who played from it (TitleMenu.forget_snapshots_of_log).
"""
import os
from typing import Any

from pygame.time import get_ticks

from src.options_screen import DEFAULT_AUTOSAVE
from src.save_state import SAVE_STATE_SLOTS, read_snapshot, state_path, take_snapshot, write_snapshot

AUTOSAVE_FILE_NAME = 'autosave.json'
# Every 3 minutes of real time on the map
AUTOSAVE_INTERVAL_MS = 3 * 60 * 1000
# The towns and castles whose entry from the overworld writes an autosave (not Hauksness, a ruin full of monsters, or
# Charlock, the Dragonlord's)
AUTOSAVE_MAPS = ('TantegelCourtyard', 'Brecconary', 'Garinham', 'Kol', 'Rimuldar', 'Cantlin')
OVERWORLD = 'Alefgard'


def autosave_path(save_dir: str) -> str:
    return os.path.join(save_dir, AUTOSAVE_FILE_NAME)


def snapshot_paths(save_dir: str) -> list[str]:
    """Every snapshot file in the save folder may be: the save states' slots and the autosave."""
    return [*(state_path(save_dir, slot) for slot in SAVE_STATE_SLOTS), autosave_path(save_dir)]


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
        # The real time the map has been played since the last autosave, and when the last frame was
        self.played_ms = 0
        self.last_frame_at = get_ticks()
        self.last_map: str | None = None
        self.entered_town = False

    @property
    def enabled(self) -> bool:
        return bool(self.game.config.get('AUTOSAVE', DEFAULT_AUTOSAVE))

    def frame(self) -> None:
        """Write the autosave if it's due (a town or castle entered from the overworld, or the interval gone by) and
        AUTOSAVE is ON. A due autosave waits for the hero to finish the step under way, so it's always written with
        the hero on a tile, as a save state is, and none is written (or time counted) while the map is held."""
        now = get_ticks()
        elapsed, self.last_frame_at = now - self.last_frame_at, now
        current = self.game.current_map.identifier
        if self.last_map == OVERWORLD and current in AUTOSAVE_MAPS:
            self.entered_town = True
        self.last_map = current
        if not self.enabled:
            self.entered_town = False
            return
        if self.game.movement.map_held:
            return
        self.played_ms += elapsed
        if self.game.player.is_moving:
            return
        if self.entered_town or self.played_ms >= AUTOSAVE_INTERVAL_MS:
            self.write()

    def restart(self) -> None:
        """Start the interval again, from now."""
        self.played_ms = 0
        self.last_frame_at = get_ticks()

    def write(self) -> None:
        """Write the autosave now; the interval starts again."""
        try:
            write_snapshot(autosave_path(self.game.directories.save_dir), take_snapshot(self.game))
        except OSError as error:
            # A full disk or a read-only save folder: play goes on, and the next autosave tries again
            print(f"Autosave failed: {error}")
        self.played_ms = 0
        self.entered_town = False
