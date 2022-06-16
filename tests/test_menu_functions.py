import os
from unittest import TestCase
from unittest.mock import patch, MagicMock

from pygame import KEYDOWN, K_RETURN, event, K_d, K_e, K_k
from pygame.time import get_ticks

from src.game import Game
from src.menu_functions import select_name

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestMenuFunctions(TestCase):
    def setUp(self) -> None:
        self.game = Game()

    def test_select_name(self):
        # mocked_k = MagicMock()
        # mocked_k.type = KEYDOWN
        # mocked_k.key = K_k
        #
        # mocked_e = MagicMock()
        # mocked_e.type = KEYDOWN
        # mocked_e.key = K_e
        #
        # mocked_d = MagicMock()
        # mocked_d.type = KEYDOWN
        # mocked_d.key = K_d

        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
            self.assertEqual('', select_name(get_ticks(), self.game.screen, self.game.cmd_menu))
