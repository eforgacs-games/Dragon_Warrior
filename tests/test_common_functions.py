import os
import unittest
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from src.common import (
    is_facing_down, is_facing_up, is_facing_left, is_facing_right,
    is_facing_medially, is_facing_laterally, set_gettext_language, find_file
)
from src.direction import Direction


class MockCharacter:
    def __init__(self, direction_value):
        self.direction_value = direction_value


class TestIsFacingFunctions(unittest.TestCase):

    def test_is_facing_down_true(self):
        char = MockCharacter(Direction.DOWN.value)
        self.assertTrue(is_facing_down(char))

    def test_is_facing_down_false(self):
        for direction in [Direction.UP, Direction.LEFT, Direction.RIGHT]:
            with self.subTest(direction=direction):
                char = MockCharacter(direction.value)
                self.assertFalse(is_facing_down(char))

    def test_is_facing_up_true(self):
        char = MockCharacter(Direction.UP.value)
        self.assertTrue(is_facing_up(char))

    def test_is_facing_up_false(self):
        for direction in [Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            with self.subTest(direction=direction):
                char = MockCharacter(direction.value)
                self.assertFalse(is_facing_up(char))

    def test_is_facing_left_true(self):
        char = MockCharacter(Direction.LEFT.value)
        self.assertTrue(is_facing_left(char))

    def test_is_facing_left_false(self):
        for direction in [Direction.DOWN, Direction.UP, Direction.RIGHT]:
            with self.subTest(direction=direction):
                char = MockCharacter(direction.value)
                self.assertFalse(is_facing_left(char))

    def test_is_facing_right_true(self):
        char = MockCharacter(Direction.RIGHT.value)
        self.assertTrue(is_facing_right(char))

    def test_is_facing_right_false(self):
        for direction in [Direction.DOWN, Direction.UP, Direction.LEFT]:
            with self.subTest(direction=direction):
                char = MockCharacter(direction.value)
                self.assertFalse(is_facing_right(char))

    def test_is_facing_medially_up(self):
        char = MockCharacter(Direction.UP.value)
        self.assertTrue(is_facing_medially(char))

    def test_is_facing_medially_down(self):
        char = MockCharacter(Direction.DOWN.value)
        self.assertTrue(is_facing_medially(char))

    def test_is_facing_medially_false_left(self):
        char = MockCharacter(Direction.LEFT.value)
        self.assertFalse(is_facing_medially(char))

    def test_is_facing_medially_false_right(self):
        char = MockCharacter(Direction.RIGHT.value)
        self.assertFalse(is_facing_medially(char))

    def test_is_facing_laterally_left(self):
        char = MockCharacter(Direction.LEFT.value)
        self.assertTrue(is_facing_laterally(char))

    def test_is_facing_laterally_right(self):
        char = MockCharacter(Direction.RIGHT.value)
        self.assertTrue(is_facing_laterally(char))

    def test_is_facing_laterally_false_up(self):
        char = MockCharacter(Direction.UP.value)
        self.assertFalse(is_facing_laterally(char))

    def test_is_facing_laterally_false_down(self):
        char = MockCharacter(Direction.DOWN.value)
        self.assertFalse(is_facing_laterally(char))

    def test_medially_and_laterally_mutually_exclusive(self):
        for direction in Direction:
            char = MockCharacter(direction.value)
            medially = is_facing_medially(char)
            laterally = is_facing_laterally(char)
            with self.subTest(direction=direction):
                # Can't be both medial and lateral at the same time
                self.assertFalse(medially and laterally)
                # Must be one or the other
                self.assertTrue(medially or laterally)


class TestSetGettextLanguage(unittest.TestCase):

    def test_english_language(self):
        _ = set_gettext_language('English')
        self.assertTrue(callable(_))
        # English gettext should pass through strings unchanged
        self.assertEqual(_('Hello'), 'Hello')

    def test_korean_language_returns_callable(self):
        # This test checks the function returns a callable without actually testing translation
        try:
            _ = set_gettext_language('Korean')
            self.assertTrue(callable(_))
        except FileNotFoundError:
            # Locale files might not be available in test environment
            self.skipTest("Korean locale files not available")

    def test_default_language_passthrough(self):
        _ = set_gettext_language('French')
        # Non-Korean language should use default gettext (passthrough)
        self.assertEqual(_('Test string'), 'Test string')


class TestFindFile(unittest.TestCase):

    def test_find_existing_file(self):
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, 'test_file.txt')
            with open(test_file, 'w') as f:
                f.write('test')

            result = find_file('test_file.txt', tmpdir)
            self.assertEqual(result, test_file)

    def test_find_nonexistent_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_file('nonexistent.txt', tmpdir)
            self.assertIsNone(result)

    def test_find_file_in_subdirectory(self):
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, 'subdir')
            os.makedirs(subdir)
            test_file = os.path.join(subdir, 'deep_file.txt')
            with open(test_file, 'w') as f:
                f.write('deep')

            result = find_file('deep_file.txt', tmpdir)
            self.assertEqual(result, test_file)


if __name__ == '__main__':
    unittest.main()
