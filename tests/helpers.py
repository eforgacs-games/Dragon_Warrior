"""Helpers shared by the test modules. Plain functions rather than pytest fixtures, so unittest TestCases can use them."""
from unittest.mock import patch

from src.calculation import Calculation
from src.config.test_config import test_config
from src.game import Game


def new_game(config: dict = test_config) -> Game:
    """A Game made from config (test_config by default: the same dict, not a copy), with pygame's SCALED display flag
    patched out while it's made, the way most tests make one."""
    with patch('src.game.SCALED'):
        return Game(config)


class _NoFrameWaitCalculation(Calculation):
    def convert_to_frames_since_start_time(self, start_time):
        return 1  # every row's frame is already over


def skip_window_frame_waits() -> None:
    """Start a patch (undo it with patch.stopall) under which the CommandMenus made from now on don't busy-wait a real
    frame for each row of a window's drop-down and drop-up effects. With NO_BLIT those loops draw nothing, so this
    only saves the wait: about 16 ms a row, which adds up over a test that opens hundreds of windows."""
    patch('src.menu.Calculation', _NoFrameWaitCalculation).start()
