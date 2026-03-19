import unittest

from src.color import BLACK, WHITE, RED, ORANGE, PINK


class TestColors(unittest.TestCase):

    def test_black(self):
        self.assertEqual(BLACK, (0, 0, 0))

    def test_white(self):
        self.assertEqual(WHITE, (255, 255, 255))

    def test_red(self):
        self.assertEqual(RED, (255, 0, 0))

    def test_orange(self):
        self.assertEqual(ORANGE, (234, 158, 34))

    def test_pink(self):
        self.assertEqual(PINK, (243, 106, 255))

    def test_colors_are_tuples(self):
        for color in [BLACK, WHITE, RED, ORANGE, PINK]:
            self.assertIsInstance(color, tuple)

    def test_colors_have_three_components(self):
        for color in [BLACK, WHITE, RED, ORANGE, PINK]:
            self.assertEqual(len(color), 3)

    def test_rgb_values_in_valid_range(self):
        for color in [BLACK, WHITE, RED, ORANGE, PINK]:
            for component in color:
                self.assertGreaterEqual(component, 0)
                self.assertLessEqual(component, 255)

    def test_black_is_darkest(self):
        black_sum = sum(BLACK)
        for color in [WHITE, RED, ORANGE, PINK]:
            self.assertGreater(sum(color), black_sum)

    def test_white_is_brightest(self):
        self.assertEqual(sum(WHITE), 765)


if __name__ == '__main__':
    unittest.main()
