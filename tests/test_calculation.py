import os
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from src.calculation import Calculation, get_tile_id_by_coordinates
from src.direction import Direction


class MockMapForCalculation:
    """Minimal map mock for calculation tests."""

    def __init__(self):
        self.layout = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8]
        ]

    def get_tile_by_value(self, value):
        tiles = {
            0: 'BRICK', 1: 'GRASS', 2: 'WATER',
            3: 'SAND', 4: 'FOREST', 5: 'MOUNTAIN',
            6: 'SWAMP', 7: 'DESERT', 8: 'CAVE'
        }
        return tiles.get(value, 'UNKNOWN')


class TestCalculationConversions(unittest.TestCase):

    def setUp(self):
        self.config = {'FPS': 60}
        self.calc = Calculation(self.config)

    def test_convert_to_frames_1000ms(self):
        self.assertAlmostEqual(self.calc.convert_to_frames(1000), 60.0)

    def test_convert_to_frames_500ms(self):
        self.assertAlmostEqual(self.calc.convert_to_frames(500), 30.0)

    def test_convert_to_frames_0ms(self):
        self.assertEqual(self.calc.convert_to_frames(0), 0)

    def test_convert_to_frames_16ms(self):
        result = self.calc.convert_to_frames(16)
        self.assertAlmostEqual(result, 0.96, places=2)

    def test_convert_to_milliseconds_60frames(self):
        self.assertAlmostEqual(self.calc.convert_to_milliseconds(60), 1000.0)

    def test_convert_to_milliseconds_30frames(self):
        self.assertAlmostEqual(self.calc.convert_to_milliseconds(30), 500.0)

    def test_convert_to_milliseconds_0frames(self):
        self.assertEqual(self.calc.convert_to_milliseconds(0), 0)

    def test_roundtrip_ms_to_frames_to_ms(self):
        original_ms = 500
        frames = self.calc.convert_to_frames(original_ms)
        back_to_ms = self.calc.convert_to_milliseconds(frames)
        self.assertAlmostEqual(back_to_ms, original_ms, places=5)

    def test_roundtrip_frames_to_ms_to_frames(self):
        original_frames = 30
        ms = self.calc.convert_to_milliseconds(original_frames)
        back_to_frames = self.calc.convert_to_frames(ms)
        self.assertAlmostEqual(back_to_frames, original_frames, places=5)

    def test_convert_to_frames_since_start_time(self):
        with patch('src.calculation.get_ticks', return_value=2000):
            result = self.calc.convert_to_frames_since_start_time(1000)
            # 1000ms elapsed * 60fps / 1000 = 60 frames
            self.assertAlmostEqual(result, 60.0)

    def test_convert_to_frames_since_start_time_no_elapsed(self):
        with patch('src.calculation.get_ticks', return_value=1000):
            result = self.calc.convert_to_frames_since_start_time(1000)
            self.assertAlmostEqual(result, 0.0)

    def test_different_fps(self):
        calc_30fps = Calculation({'FPS': 30})
        self.assertAlmostEqual(calc_30fps.convert_to_frames(1000), 30.0)
        self.assertAlmostEqual(calc_30fps.convert_to_milliseconds(30), 1000.0)


class TestGetDistanceFromTantegel(unittest.TestCase):

    def test_at_tantegel(self):
        col_dist, row_dist = Calculation.get_distance_from_tantegel(51, 50)
        self.assertEqual(col_dist, 0)
        self.assertEqual(row_dist, 0)

    def test_east_of_tantegel(self):
        col_dist, row_dist = Calculation.get_distance_from_tantegel(55, 50)
        self.assertEqual(col_dist, 4)
        self.assertEqual(row_dist, 0)

    def test_south_of_tantegel(self):
        col_dist, row_dist = Calculation.get_distance_from_tantegel(51, 53)
        self.assertEqual(col_dist, 0)
        self.assertEqual(row_dist, 3)

    def test_west_of_tantegel(self):
        col_dist, row_dist = Calculation.get_distance_from_tantegel(46, 50)
        self.assertEqual(col_dist, -5)
        self.assertEqual(row_dist, 0)

    def test_north_of_tantegel(self):
        col_dist, row_dist = Calculation.get_distance_from_tantegel(51, 47)
        self.assertEqual(col_dist, 0)
        self.assertEqual(row_dist, -3)

    def test_diagonal_from_tantegel(self):
        col_dist, row_dist = Calculation.get_distance_from_tantegel(56, 53)
        self.assertEqual(col_dist, 5)
        self.assertEqual(row_dist, 3)


class TestGetNextTileIdentifier(unittest.TestCase):

    def setUp(self):
        self.mock_map = MockMapForCalculation()

    def test_next_tile_up(self):
        # From (col=1, row=1) going UP -> row 0
        # layout[0][1] = 1 = GRASS
        result = Calculation.get_next_tile_identifier(1, 1, Direction.UP.value, self.mock_map)
        self.assertEqual(result, 'GRASS')

    def test_next_tile_down(self):
        # From (col=1, row=1) going DOWN -> row 2
        # layout[2][1] = 7 = DESERT
        result = Calculation.get_next_tile_identifier(1, 1, Direction.DOWN.value, self.mock_map)
        self.assertEqual(result, 'DESERT')

    def test_next_tile_left(self):
        # From (col=1, row=1) going LEFT -> col 0
        # layout[1][0] = 3 = SAND
        result = Calculation.get_next_tile_identifier(1, 1, Direction.LEFT.value, self.mock_map)
        self.assertEqual(result, 'SAND')

    def test_next_tile_right(self):
        # From (col=1, row=1) going RIGHT -> col 2
        # layout[1][2] = 5 = MOUNTAIN
        result = Calculation.get_next_tile_identifier(1, 1, Direction.RIGHT.value, self.mock_map)
        self.assertEqual(result, 'MOUNTAIN')

    def test_next_tile_with_offset_2(self):
        # From (col=0, row=0) going RIGHT with offset=2 -> col 2
        # layout[0][2] = 2 = WATER
        result = Calculation.get_next_tile_identifier(0, 0, Direction.RIGHT.value, self.mock_map, offset=2)
        self.assertEqual(result, 'WATER')

    def test_next_tile_up_from_top_row(self):
        # From (col=0, row=0) going UP -> row -1
        # Python negative indexing wraps: layout[-1][0] = 6 = 'SWAMP'
        result = Calculation.get_next_tile_identifier(0, 0, Direction.UP.value, self.mock_map)
        self.assertEqual(result, 'SWAMP')

    def test_next_tile_corner(self):
        # From (col=0, row=0) going DOWN
        # layout[1][0] = 3 = SAND
        result = Calculation.get_next_tile_identifier(0, 0, Direction.DOWN.value, self.mock_map)
        self.assertEqual(result, 'SAND')


class TestGetTileIdByCoordinates(unittest.TestCase):

    def setUp(self):
        self.mock_map = MockMapForCalculation()

    def test_origin(self):
        result = get_tile_id_by_coordinates(0, 0, self.mock_map)
        self.assertEqual(result, 'BRICK')

    def test_middle(self):
        result = get_tile_id_by_coordinates(1, 1, self.mock_map)
        self.assertEqual(result, 'FOREST')

    def test_bottom_right(self):
        result = get_tile_id_by_coordinates(2, 2, self.mock_map)
        self.assertEqual(result, 'CAVE')

    def test_top_right(self):
        result = get_tile_id_by_coordinates(2, 0, self.mock_map)
        self.assertEqual(result, 'WATER')

    def test_row_out_of_bounds(self):
        result = get_tile_id_by_coordinates(0, 10, self.mock_map)
        self.assertIsNone(result)

    def test_column_out_of_bounds(self):
        result = get_tile_id_by_coordinates(10, 0, self.mock_map)
        self.assertIsNone(result)

    def test_negative_row_wraps(self):
        # Python negative indexing: layout[-1][0] = 6 = 'SWAMP'
        result = get_tile_id_by_coordinates(0, -1, self.mock_map)
        self.assertEqual(result, 'SWAMP')

    def test_first_column_last_row(self):
        result = get_tile_id_by_coordinates(0, 2, self.mock_map)
        self.assertEqual(result, 'SWAMP')


if __name__ == '__main__':
    unittest.main()
