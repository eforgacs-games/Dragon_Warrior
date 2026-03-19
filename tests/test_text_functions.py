import os
import unittest
from unittest.mock import patch, MagicMock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.text import DialogBoxWrapper, set_text_rect_alignment, set_font_by_ascii_chars


class TestDialogBoxWrapper(unittest.TestCase):

    def setUp(self):
        self.wrapper = DialogBoxWrapper(width=21, break_long_words=False)

    def test_simple_text_wraps(self):
        result = self.wrapper.wrap("Hello world this is a test of wrapping")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_newline_creates_separate_lines(self):
        result = self.wrapper.wrap("Line one\nLine two")
        self.assertGreaterEqual(len(result), 2)
        # Both lines should appear in the result
        self.assertTrue(any('Line one' in line for line in result))
        self.assertTrue(any('Line two' in line for line in result))

    def test_short_text_single_line(self):
        result = self.wrapper.wrap("Short")
        self.assertEqual(result, ["Short"])

    def test_empty_string(self):
        result = self.wrapper.wrap("")
        self.assertIsInstance(result, list)

    def test_multiple_newlines(self):
        result = self.wrapper.wrap("A\nB\nC")
        # Should produce at least 3 items
        self.assertGreaterEqual(len(result), 3)

    def test_long_line_gets_wrapped(self):
        long_text = "This is a very long line that should be wrapped at the boundary"
        result = self.wrapper.wrap(long_text)
        self.assertGreater(len(result), 1)

    def test_wrap_respects_width(self):
        result = self.wrapper.wrap("Hello world testing the width")
        for line in result:
            self.assertLessEqual(len(line), 21)

    def test_newline_in_middle(self):
        result = self.wrapper.wrap("First part\nSecond part that is longer than the first")
        # Verify both original lines are represented
        full_text = ' '.join(result)
        self.assertIn('First', full_text)
        self.assertIn('Second', full_text)


class TestSetTextRectAlignment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((800, 600))
        cls.font = pygame.font.Font(None, 16)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _make_surface(self, text):
        return self.font.render(text, True, (255, 255, 255))

    def test_left_alignment(self):
        surface = self._make_surface("Test")
        rect = set_text_rect_alignment('left', surface, 100, 200)
        self.assertEqual(rect.midleft, (100, 200))

    def test_center_alignment(self):
        surface = self._make_surface("Test")
        rect = set_text_rect_alignment('center', surface, 100, 200)
        self.assertEqual(rect.midtop, (100, 200))

    def test_right_alignment(self):
        surface = self._make_surface("Test")
        rect = set_text_rect_alignment('right', surface, 100, 200)
        self.assertEqual(rect.midright, (100, 200))

    def test_returns_rect(self):
        surface = self._make_surface("Test")
        rect = set_text_rect_alignment('left', surface, 0, 0)
        self.assertIsInstance(rect, pygame.Rect)

    def test_left_alignment_at_origin(self):
        surface = self._make_surface("X")
        rect = set_text_rect_alignment('left', surface, 0, 0)
        self.assertEqual(rect.midleft[0], 0)
        self.assertEqual(rect.midleft[1], 0)

    def test_center_x_position(self):
        surface = self._make_surface("Center")
        rect = set_text_rect_alignment('center', surface, 400, 300)
        self.assertEqual(rect.midtop[0], 400)
        self.assertEqual(rect.midtop[1], 300)


class TestSetFontByAsciiChars(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_ascii_chunks_uses_dq_font(self):
        mock_dirs = MagicMock()
        mock_dirs.DRAGON_QUEST_FONT_PATH = 'some/dq/font.ttf'
        mock_font_instance = MagicMock()
        with patch('src.text.font.Font', return_value=mock_font_instance) as mock_font_class:
            result = set_font_by_ascii_chars(['Hello World'], 16, None, mock_dirs)
            mock_font_class.assert_called_with('some/dq/font.ttf', 16)
            self.assertEqual(result, mock_font_instance)

    def test_non_ascii_chunks_uses_unifont(self):
        mock_dirs = MagicMock()
        mock_dirs.UNIFONT_PATH = 'some/unifont.ttf'
        mock_font_instance = MagicMock()
        with patch('src.text.font.Font', return_value=mock_font_instance) as mock_font_class:
            set_font_by_ascii_chars(['한글 텍스트'], 16, None, mock_dirs)
            mock_font_class.assert_called_with('some/unifont.ttf', 16)

    def test_explicit_font_name_overrides_selection(self):
        mock_dirs = MagicMock()
        mock_font_instance = MagicMock()
        with patch('src.text.font.Font', return_value=mock_font_instance) as mock_font_class:
            result = set_font_by_ascii_chars(['Hello'], 16, 'custom_font.ttf', mock_dirs)
            mock_font_class.assert_called_with('custom_font.ttf', 16)
            self.assertEqual(result, mock_font_instance)

    def test_non_ascii_sets_bold(self):
        mock_dirs = MagicMock()
        mock_dirs.UNIFONT_PATH = 'unifont.ttf'
        mock_font_instance = MagicMock()
        mock_font_instance.bold = False
        with patch('src.text.font.Font', return_value=mock_font_instance):
            set_font_by_ascii_chars(['한글'], 16, None, mock_dirs)
            self.assertTrue(mock_font_instance.bold)


if __name__ == '__main__':
    unittest.main()
