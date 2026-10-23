"""Helpers shared by the test modules. Plain functions rather than pytest fixtures, so unittest TestCases can use them."""
from unittest.mock import patch

from src.config.test_config import test_config
from src.game import Game


def new_game(config: dict = test_config) -> Game:
    """A Game made from config (test_config by default: the same dict, not a copy), with pygame's SCALED display flag
    patched out while it's made, the way most tests make one."""
    with patch('src.game.SCALED'):
        return Game(config)
