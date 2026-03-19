import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from src.maps_functions import warp_line, get_center_point


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

    def test_horizontal_two_points(self):
        result = warp_line((0, 0), (1, 0))
        self.assertEqual(result, [(0, 0), (1, 0)])

    def test_vertical_two_points(self):
        result = warp_line((0, 0), (0, 1))
        self.assertEqual(result, [(0, 0), (0, 1)])

    def test_horizontal_includes_endpoints(self):
        result = warp_line((2, 7), (5, 7))
        self.assertIn((2, 7), result)
        self.assertIn((5, 7), result)

    def test_vertical_includes_endpoints(self):
        result = warp_line((3, 1), (3, 4))
        self.assertIn((3, 1), result)
        self.assertIn((3, 4), result)

    def test_horizontal_correct_length(self):
        result = warp_line((0, 0), (4, 0))
        self.assertEqual(len(result), 5)

    def test_vertical_correct_length(self):
        result = warp_line((0, 0), (0, 4))
        self.assertEqual(len(result), 5)

    def test_diagonal_raises_assertion_error(self):
        with self.assertRaises(AssertionError):
            warp_line((0, 0), (3, 4))

    def test_horizontal_y_is_constant(self):
        result = warp_line((0, 7), (5, 7))
        for pt in result:
            self.assertEqual(pt[1], 7)

    def test_vertical_x_is_constant(self):
        result = warp_line((3, 0), (3, 5))
        for pt in result:
            self.assertEqual(pt[0], 3)

    def test_result_is_list(self):
        result = warp_line((0, 0), (3, 0))
        self.assertIsInstance(result, list)

    def test_result_elements_are_tuples(self):
        result = warp_line((0, 0), (3, 0))
        for item in result:
            self.assertIsInstance(item, tuple)

    def test_longer_horizontal_line(self):
        result = warp_line((0, 10), (9, 10))
        expected_x_values = list(range(10))
        for i, pt in enumerate(result):
            self.assertEqual(pt[0], expected_x_values[i])
            self.assertEqual(pt[1], 10)


class TestGetCenterPoint(unittest.TestCase):

    def test_center_at_origin(self):
        result = get_center_point(0, 0, 32)
        self.assertEqual(result, (16, 16))

    def test_center_at_tile_1_1(self):
        result = get_center_point(1, 1, 32)
        self.assertEqual(result, (48, 48))

    def test_center_with_tile_size_16(self):
        result = get_center_point(0, 0, 16)
        self.assertEqual(result, (8, 8))

    def test_center_at_tile_2_3(self):
        result = get_center_point(2, 3, 32)
        expected_x = 2 * 32 + 16
        expected_y = 3 * 32 + 16
        self.assertEqual(result, (expected_x, expected_y))

    def test_center_returns_tuple(self):
        result = get_center_point(1, 1, 16)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_center_offset_is_half_tile_size(self):
        tile_size = 32
        x, y = 5, 3
        result = get_center_point(x, y, tile_size)
        expected_x = x * tile_size + tile_size // 2
        expected_y = y * tile_size + tile_size // 2
        self.assertEqual(result, (expected_x, expected_y))

    def test_center_with_tile_size_64(self):
        result = get_center_point(1, 1, 64)
        self.assertEqual(result, (96, 96))

    def test_center_at_origin_tile_size_1(self):
        result = get_center_point(0, 0, 1)
        self.assertEqual(result, (0, 0))

    def test_center_large_coordinates(self):
        result = get_center_point(100, 100, 32)
        self.assertEqual(result, (3216, 3216))


if __name__ == '__main__':
    unittest.main()
