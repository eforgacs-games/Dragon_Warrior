from unittest import TestCase

from src.common import Direction
from src.game import Game
from src.maps import MapWithoutNPCs

layout = [[33, 0, 3],
          [4, 2, 3],
          [3, 3, 39]]

# os.environ["SDL_VIDEODRIVER"] = "dummy"
# os.environ['SDL_AUDIODRIVER'] = 'dummy'

class MockMap(MapWithoutNPCs):
    __test__ = False

    def __init__(self):
        super().__init__(layout)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value


class TestCommandMenu(TestCase):

    def setUp(self) -> None:
        self.game = Game()
        self.game.current_map = MockMap()
        self.game.current_map.load_map(self.game.player)

    # def test_take(self):
        # pygame.key.get_pressed = create_key_mock(pygame.K_s)
        # self.game.cmd_menu.take()
        # pygame.key.get_pressed = create_key_mock(pygame.K_k)
        # self.assertEqual(self.game.current_map.tile_key['BRICK']['val'],
        #                  self.game.current_map.layout[0][1])
