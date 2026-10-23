from unittest import TestCase

from src.calculation import Calculation
from src.config.test_config import test_config
from src.drawer import get_surrounding_tile_values

layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 39]]

calculation = Calculation(test_config)


class Test(TestCase):
    def test_get_surrounding_tile_values(self):
        self.assertEqual({0, 1, 2, 3}, get_surrounding_tile_values((1, 1), layout))
        self.assertEqual({0, 3}, get_surrounding_tile_values((0, 2), layout))
        self.assertEqual({1, 3}, get_surrounding_tile_values((2, 0), layout))
        self.assertEqual({0, 1, 33}, get_surrounding_tile_values((0, 0), layout))
        self.assertEqual({3, 39}, get_surrounding_tile_values((2, 2), layout))
        self.assertEqual({39}, get_surrounding_tile_values((2, 3), layout))
        self.assertEqual({3, 39}, get_surrounding_tile_values((-1, 2), layout))
        self.assertEqual({3, 39}, get_surrounding_tile_values((2, -1), layout))
        self.assertEqual({39}, get_surrounding_tile_values((3, 2), layout))

    def test_convert_to_frames(self):
        self.assertAlmostEqual(0.600988, calculation.convert_to_frames(10), places=6)

    def test_nine_slice_keeps_the_border(self):
        from pygame import Surface
        from src.common import nine_slice
        source = Surface((24, 24))
        source.fill((0, 0, 0))
        # A one pixel frame and a mark in the top left corner
        for i in range(24):
            for x, y in ((i, 0), (i, 23), (0, i), (23, i)):
                source.set_at((x, y), (255, 255, 255))
        source.set_at((2, 2), (255, 0, 0))
        result = nine_slice(source, (40, 64), 8)
        self.assertEqual((40, 64), result.get_size())
        self.assertEqual((255, 0, 0, 255), tuple(result.get_at((2, 2))))
        # The frame stays one pixel thick on every side
        for x, y in ((20, 0), (20, 63), (0, 32), (39, 32)):
            self.assertEqual((255, 255, 255, 255), tuple(result.get_at((x, y))))
        for x, y in ((20, 1), (20, 62), (1, 32), (38, 32)):
            self.assertEqual((0, 0, 0, 255), tuple(result.get_at((x, y))))
