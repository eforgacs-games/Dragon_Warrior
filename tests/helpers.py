"""Helpers shared by the test modules. Plain functions rather than pytest fixtures, so unittest TestCases can use them."""
from unittest.mock import patch

from src.config.test_config import test_config
from src.game import Game
from src.waiting import frames_to_ms, game_speed


def new_game(config: dict = test_config) -> Game:
    """A Game made from config (test_config by default: the same dict, not a copy), with pygame's SCALED display flag
    patched out while it's made, the way most tests make one."""
    with patch('src.game.SCALED'):
        return Game(config)


def skip_window_frame_waits() -> None:
    """Start a patch (undo it with patch.stopall) under which a window's drop-down and drop-up effects don't wait a
    real frame for each row. With NO_BLIT those effects draw nothing, so this only saves the wait: about 16 ms a row,
    which adds up over a test that opens hundreds of windows."""
    patch('src.menu.wait_for_next_window_row').start()


class FakeClock:
    """A stand-in for pygame's millisecond clock: ``get_ticks`` only moves when ``wait`` is called (a wait returns at
    once, having moved the clock on by its length) or the test moves it on itself. Under it every timer in the game,
    the game clock (``src.waiting.game_ticks``), FramePacer, the dialogs' and battles' waits, runs on the test's time,
    so a test of the real loops does the same thing however busy the machine is."""

    def __init__(self, start_ms: int = 0):
        self.ms = start_ms

    def get_ticks(self) -> int:
        return int(self.ms)

    def wait(self, milliseconds: int) -> int:
        self.ms += max(0, milliseconds)
        return max(0, milliseconds)

    delay = wait

    def advance_frames(self, frames: float = 1) -> None:
        """Move the clock on by ``frames`` NES frames of game time, at the current game speed."""
        self.ms += frames_to_ms(frames) / game_speed()


def fake_game_clock(start_ms: int = 0) -> FakeClock:
    """Start a patch (undo it with patch.stopall) that puts pygame's ``time.get_ticks``, ``time.wait`` and
    ``time.delay`` on a FakeClock, and starts the game clock over at speed 1 on it (patched too, so stopping the
    patches puts the game clock back as it was)."""
    clock = FakeClock(start_ms)
    patch('pygame.time.get_ticks', clock.get_ticks).start()
    patch('pygame.time.wait', clock.wait).start()
    patch('pygame.time.delay', clock.delay).start()
    for name, value in (('_speed', 1), ('_real_anchor', 0), ('_game_anchor', 0), ('_rounding_carry', 0.0)):
        patch(f'src.waiting.{name}', value).start()
    return clock
