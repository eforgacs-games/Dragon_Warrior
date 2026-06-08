import os
import unittest
from unittest.mock import MagicMock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.maps_functions import warp_line, get_center_point, parse_animated_sprite_sheet
from src.config.test_config import test_config


class TestWarpLine(unittest.TestCase):

    def test_horizontal_line(self):
        result = warp_line((0, 5), (3, 5))
        self.assertEqual(result, [(0, 5), (1, 5), (2, 5), (3, 5)])

    def test_vertical_line(self):
        result = warp_line((5, 0), (5, 3))
        self.assertEqual(result, [(5, 0), (5, 1), (5, 2), (5, 3)])

    def test_single_point(self):
        result = warp_line((2, 2), (2, 2))
        self.assertEqual(result, [(2, 2)])

    def test_diagonal_raises_assertion_error(self):
        with self.assertRaises(AssertionError):
            warp_line((0, 0), (3, 4))

    def test_horizontal_returns_list_of_tuples(self):
        result = warp_line((0, 0), (2, 0))
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIsInstance(item, tuple)

    def test_horizontal_y_is_constant(self):
        result = warp_line((0, 7), (5, 7))
        for pt in result:
            self.assertEqual(pt[1], 7)

    def test_vertical_x_is_constant(self):
        result = warp_line((3, 0), (3, 5))
        for pt in result:
            self.assertEqual(pt[0], 3)

    def test_horizontal_includes_both_endpoints(self):
        result = warp_line((2, 7), (5, 7))
        self.assertIn((2, 7), result)
        self.assertIn((5, 7), result)

    def test_horizontal_correct_length(self):
        result = warp_line((0, 0), (4, 0))
        self.assertEqual(len(result), 5)

    def test_vertical_correct_length(self):
        result = warp_line((0, 0), (0, 4))
        self.assertEqual(len(result), 5)


class TestGetCenterPoint(unittest.TestCase):

    def test_formula_matches_expected(self):
        tile_size = 32
        for x, y in [(0, 0), (1, 1), (3, 5), (10, 7)]:
            with self.subTest(x=x, y=y):
                expected = (x * tile_size + tile_size // 2, y * tile_size + tile_size // 2)
                self.assertEqual(get_center_point(x, y, tile_size), expected)

    def test_origin_tile_size_32(self):
        self.assertEqual(get_center_point(0, 0, 32), (16, 16))

    def test_tile_1_1_tile_size_32(self):
        self.assertEqual(get_center_point(1, 1, 32), (48, 48))

    def test_tile_size_16(self):
        self.assertEqual(get_center_point(0, 0, 16), (8, 8))

    def test_returns_tuple_of_two(self):
        result = get_center_point(1, 1, 32)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_large_coordinates(self):
        self.assertEqual(get_center_point(100, 100, 32), (3216, 3216))


class TestParseAnimatedSpriteSheet(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((256, 240))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _make_surface(self, width, height):
        """Create a real pygame Surface of the given dimensions."""
        surf = pygame.Surface((width, height))
        surf.fill((0, 0, 0))
        return surf

    def test_returns_four_lists(self):
        tile_size = test_config['TILE_SIZE']
        # A four-sided sprite sheet needs 8 columns of tile_size width.
        # Width must be divisible by 128 and wide enough for (i+6)*tile_size rects.
        # With tile_size=32: 8 * 32 = 256; 256 % 128 == 0 ✓
        width = tile_size * 8
        surf = self._make_surface(width, tile_size)
        result = parse_animated_sprite_sheet(surf, test_config)
        self.assertEqual(len(result), 4)
        for lst in result:
            self.assertIsInstance(lst, list)

    def test_four_sided_sheet_all_lists_populated(self):
        tile_size = test_config['TILE_SIZE']
        # 8-column sheet (width % 128 == 0) → all four direction lists filled
        width = tile_size * 8
        surf = self._make_surface(width, tile_size)
        facing_down, facing_left, facing_up, facing_right = parse_animated_sprite_sheet(surf, test_config)
        self.assertEqual(len(facing_down), 2)
        self.assertEqual(len(facing_left), 2)
        self.assertEqual(len(facing_up), 2)
        self.assertEqual(len(facing_right), 2)

    def test_non_four_sided_sheet_has_only_facing_down(self):
        tile_size = test_config['TILE_SIZE']
        # Width not divisible by 128 (2 tiles wide) → only facing_down populated
        width = tile_size * 2  # e.g. 64 — not divisible by 128
        surf = self._make_surface(width, tile_size)
        facing_down, facing_left, facing_up, facing_right = parse_animated_sprite_sheet(surf, test_config)
        self.assertEqual(len(facing_down), 2)
        self.assertEqual(len(facing_left), 0)
        self.assertEqual(len(facing_up), 0)
        self.assertEqual(len(facing_right), 0)

    def test_facing_down_has_two_frames(self):
        tile_size = test_config['TILE_SIZE']
        width = tile_size * 8
        surf = self._make_surface(width, tile_size)
        facing_down, _, _, _ = parse_animated_sprite_sheet(surf, test_config)
        self.assertEqual(len(facing_down), 2)


if __name__ == '__main__':
    unittest.main()
