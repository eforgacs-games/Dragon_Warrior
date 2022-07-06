import os
from unittest import TestCase
from unittest.mock import patch

from src.common import Direction
from src.game import Game
from src.maps import MapWithoutNPCs

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['SDL_AUDIODRIVER'] = 'dummy'

layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 39]]


class MockMap(MapWithoutNPCs):
    __test__ = False

    def __init__(self):
        super().__init__(layout)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value


class TestCamera(TestCase):
    def setUp(self) -> None:
        with patch('src.game.SCALED'):
            self.game = Game()
        self.game.camera_pos = 0, 0
        self.center_pt = 0, 0

    def test_set_pos(self):
        self.game.camera.set_pos((1, 2))
        self.assertEqual(1, self.game.camera.x)
        self.assertEqual(2, self.game.camera.y)
