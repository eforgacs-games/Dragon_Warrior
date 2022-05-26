from unittest import TestCase

from src.common import get_surrounding_tile_values

layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 39]]


class Test(TestCase):
    def test_get_surrounding_tile_values(self):
        self.assertEqual({0, 1, 2, 3}, get_surrounding_tile_values((1, 1), layout))
        self.assertEqual({0, 3}, get_surrounding_tile_values((0, 2), layout))
        self.assertEqual({1, 3}, get_surrounding_tile_values((2, 0), layout))
