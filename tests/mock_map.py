import os

from src.direction import Direction
from src.maps import MapWithoutNPCs

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 39]]


class MockMap(MapWithoutNPCs):
    __test__ = False

    def __init__(self, config):
        super().__init__(layout, config, None, (0, 0))

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value
