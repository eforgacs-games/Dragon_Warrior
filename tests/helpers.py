"""Helpers shared by the test modules. Plain functions rather than pytest fixtures, so unittest TestCases can use them."""
from unittest.mock import patch

from src.config.test_config import test_config
from src.game import Game


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
