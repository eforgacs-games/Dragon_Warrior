"""Rewind: hold Backspace on the map to step the game back in time. Not NES; quality of life, like an emulator's.

The game keeps the last REWIND_CAPACITY snapshots in memory (``snapshots``), the same snapshots a save state holds
(src/save_state.py take_snapshot): one every REWIND_INTERVAL_FRAMES map frames while the map is being played (60
of them, 30 frames apart, are 30 seconds at normal speed), and one taken just before every fight starts. They are
taken between two map frames, so putting one back and pressing the same keys plays out as it did.

- Backspace on the map, when START would be accepted (no window open or asked for), starts rewinding
  (``start``): the newest snapshot is put back at once, then, while Backspace is held, the one before it every
  REWIND_STEP_MS real milliseconds (about 4 frames at 60 Hz, at any game speed), each drawn as it is put back. Nothing
  else runs meanwhile: the map frames wait (Game.run_due_frames), and other keys are ignored.
- Letting go (``stop``) carries on from the snapshot on screen; the snapshots after it are dropped.
- In a fight there is no rewinding: the fight's own loops read the keys. A fight starts in the middle of a map frame,
  so the snapshot taken before it is the one from the start of that frame (``before_frame`` takes one whenever the
  hero's step, a hill's pause or a scripted fight might start a fight in this frame, and ``fight_starts`` keeps it).
  After the fight, rewinding reaches it first, unless a periodic one was taken since.

Snapshots are small (no surfaces; see save_state), so 60 of them take a few hundred KB (tests/test_rewind.py
measures them).
"""
from collections import deque
from typing import Any

from pygame import time

from src.direction import Direction
from src.save_state import restore_snapshot, take_snapshot

REWIND_INTERVAL_FRAMES = 30
REWIND_CAPACITY = 60
# How long each snapshot stays on screen while rewinding, in real milliseconds (4 frames at 60 Hz)
REWIND_STEP_MS = 4 * 1000 // 60


class Rewind:
    """The snapshots and the rewinding (see the module docstring)."""

    def __init__(self, game: Any) -> None:
        self.game = game
        self.snapshots: deque[dict[str, Any]] = deque(maxlen=REWIND_CAPACITY)
        self.frames_since_snapshot = 0
        # The snapshot from the start of a map frame that may start a fight (before_frame)
        self.fight_candidate: dict[str, Any] | None = None
        self.active = False
        # While rewinding: the index in snapshots of the one on screen, and when it was put back (real ms)
        self.position = 0
        self.shown_at = 0

    def on_the_map(self) -> bool:
        """Whether the map is being played: nothing open, asked for or waiting, as when START would be accepted."""
        movement = self.game.movement
        return not (movement.world_frozen or movement.freeze_pending)

    # Recording

    def record(self) -> None:
        self.snapshots.append(take_snapshot(self.game))
        self.frames_since_snapshot = 0

    def before_frame(self) -> None:
        """At the start of a map frame: keep a snapshot if a fight may start in it."""
        self.fight_candidate = take_snapshot(self.game) if self.fight_may_start() else None

    def fight_may_start(self) -> bool:
        """Whether this map frame may start a fight: a scripted fight is waiting (Game.handle_battles), a hill's pause
        ends (MovementController.hill_pause_frame) or the hero's step ends (Game.handle_battles, the guardians)."""
        game = self.game
        if game.battle_ctrl.pending_scripted_battle is not None or game.movement.hill_pause_frames == 1:
            return True
        player = game.player
        if not player.is_moving:
            return False
        # The hero moves `speed` pixels a frame; the step ends on the frame that brings him onto a tile
        tile_size, speed = game.tile_size, game.movement.speed
        direction = player.direction_value
        offset = (player.rect.x if direction in (Direction.LEFT, Direction.RIGHT) else player.rect.y) % tile_size
        return offset == (speed if direction in (Direction.UP, Direction.LEFT) else tile_size - speed)

    def fight_starts(self) -> None:
        """A fight is starting (BattleController.launch_fight): keep the snapshot from the start of this frame."""
        if self.fight_candidate is not None:
            self.snapshots.append(self.fight_candidate)
            self.fight_candidate = None

    def after_frame(self) -> None:
        """At the end of a map frame: count it, if the map was being played, and take a snapshot every
        REWIND_INTERVAL_FRAMES of them."""
        if not self.on_the_map():
            return
        self.frames_since_snapshot += 1
        if self.frames_since_snapshot >= REWIND_INTERVAL_FRAMES:
            self.record()

    # Rewinding

    def start(self) -> bool:
        """Backspace pressed on the map: put the newest snapshot back. Returns whether rewinding started."""
        if self.active or not self.snapshots or not self.on_the_map():
            return False
        self.active = True
        self.show(len(self.snapshots) - 1)
        return True

    def update(self) -> None:
        """While Backspace is held (once per main loop frame): go back one snapshot every REWIND_STEP_MS."""
        if self.active and self.position > 0 and time.get_ticks() - self.shown_at >= REWIND_STEP_MS:
            self.step_back()

    def step_back(self) -> None:
        if self.position > 0:
            self.show(self.position - 1)

    def show(self, position: int) -> None:
        self.position = position
        restore_snapshot(self.game, self.snapshots[position], fade_in=False)
        self.shown_at = time.get_ticks()

    def stop(self) -> None:
        """Backspace let go: play on from the snapshot on screen, dropping the ones after it."""
        if not self.active:
            return
        self.active = False
        while len(self.snapshots) > self.position + 1:
            self.snapshots.pop()
        self.frames_since_snapshot = 0
        self.fight_candidate = None
