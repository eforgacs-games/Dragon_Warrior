import unittest
from enum import IntEnum

from src.direction import Direction


class TestDirection(unittest.TestCase):

    def test_direction_is_int_enum(self):
        self.assertTrue(issubclass(Direction, IntEnum))

    def test_down_value(self):
        self.assertEqual(Direction.DOWN.value, 0)

    def test_left_value(self):
        self.assertEqual(Direction.LEFT.value, 1)

    def test_up_value(self):
        self.assertEqual(Direction.UP.value, 2)

    def test_right_value(self):
        self.assertEqual(Direction.RIGHT.value, 3)

    def test_direction_count(self):
        self.assertEqual(len(Direction), 4)

    def test_direction_comparison_with_int(self):
        self.assertTrue(Direction.DOWN == 0)
        self.assertTrue(Direction.LEFT == 1)
        self.assertTrue(Direction.UP == 2)
        self.assertTrue(Direction.RIGHT == 3)

    def test_direction_from_value(self):
        self.assertEqual(Direction(0), Direction.DOWN)
        self.assertEqual(Direction(1), Direction.LEFT)
        self.assertEqual(Direction(2), Direction.UP)
        self.assertEqual(Direction(3), Direction.RIGHT)

    def test_direction_names(self):
        self.assertEqual(Direction.DOWN.name, 'DOWN')
        self.assertEqual(Direction.LEFT.name, 'LEFT')
        self.assertEqual(Direction.UP.name, 'UP')
        self.assertEqual(Direction.RIGHT.name, 'RIGHT')

    def test_invalid_direction_raises(self):
        with self.assertRaises(ValueError):
            Direction(99)

    def test_direction_ordering(self):
        self.assertLess(Direction.DOWN, Direction.LEFT)
        self.assertLess(Direction.LEFT, Direction.UP)
        self.assertLess(Direction.UP, Direction.RIGHT)

    def test_all_members(self):
        members = list(Direction)
        self.assertIn(Direction.DOWN, members)
        self.assertIn(Direction.LEFT, members)
        self.assertIn(Direction.UP, members)
        self.assertIn(Direction.RIGHT, members)


if __name__ == '__main__':
    unittest.main()
