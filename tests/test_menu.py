import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from pygame import KEYDOWN, K_RETURN, event

from src.direction import Direction
from src.config import prod_config
from src.game import Game
from src.maps import MapWithoutNPCs

layout = [[33, 0, 3],
          [4, 2, 3],
          [3, 3, 39]]

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class MockMap(MapWithoutNPCs):
    __test__ = False

    def __init__(self):
        super().__init__(layout)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value


class TestCommandMenu(TestCase):

    @patch('src.game.Game.set_screen')
    def setUp(self, mock_set_screen) -> None:
        with patch('src.game.SCALED'):
            self.game = Game(prod_config)
        self.game.current_map = MockMap()
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
