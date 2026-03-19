import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_RETURN, event

from src.config.test_config import test_config
from src.game import Game
from tests.mock_map import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestCommandMenu(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])

    # def test_take(self):
    # pygame.key.get_pressed = create_key_mock(pygame.K_s)
    # self.game.cmd_menu.take()
    # pygame.key.get_pressed = create_key_mock(pygame.K_k)
    # self.assertEqual(self.game.current_map.tile_key['BRICK']['val'],
    #                  self.game.current_map.layout[0][1])

    def test_npc_is_across_counter(self):
        self.assertFalse(self.game.cmd_menu.npc_is_across_counter(self.game.current_map.characters['HERO']))

    def test_take_item(self):
        self.assertEqual([], self.game.player.inventory)
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
            self.game.cmd_menu.take_item("test_item")
        self.assertIn("test_item", self.game.player.inventory)

    def test_take_gold(self):
        self.assertEqual(0, self.game.player.gold)
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
            self.game.cmd_menu.take_gold({'item': 'GOLD', 'amount': 120})
        self.assertEqual(120, self.game.player.gold)
