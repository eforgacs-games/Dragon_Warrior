from unittest import TestCase

import pygame

from data.text.intro_lookup_table import ControlInfo
from src.config.test_config import test_config
from src.directories import Directories
from src.text import DialogBoxWrapper, WRAP_LENGTH, set_font_by_ascii_chars

# The dialog box (CommandMenu.show_text_line_in_dialog_box) is 12 tiles wide from tile 2, with text starting at
# tile 3. Its rows are 17 px apart from 9.75 tiles down, and the continue arrow blinks just under the fifth row.
MAX_ROWS_PER_PAGE = 5
DEBUG_KEY_LINES = ("F5: Warp", "F6: Give item/gold/level", "F7: Load checkpoint")


def wrapped_rows(page: str) -> list[str]:
    """The rows draw_text puts on screen for one page."""
    return DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False).wrap(page)


class TestControlInfoHelpPages(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def help_pages(self, debug_keys: bool, language: str = 'English') -> tuple[str, ...]:
        return ControlInfo({**test_config, 'DEBUG_KEYS': debug_keys, 'LANGUAGE': language}).help_pages

    def test_page_count(self):
        # the quest journal (#410) and the dungeon map (#408) have a page each
        self.assertEqual(9, len(self.help_pages(debug_keys=False)))
        self.assertEqual(10, len(self.help_pages(debug_keys=True)))

    def test_every_control_is_on_a_page(self):
        for debug_keys in (False, True):
            control_info = ControlInfo({**test_config, 'DEBUG_KEYS': debug_keys})
            lines = [line for page in control_info.help_pages for line in page.split('\n')]
            for control in control_info.controls:
                self.assertIn(control, lines)

    def test_debug_keys_only_with_debug_keys_on(self):
        for line in DEBUG_KEY_LINES:
            self.assertNotIn(line, "\n".join(self.help_pages(debug_keys=False)))
        pages = self.help_pages(debug_keys=True)
        self.assertEqual(("Debug keys:",) + DEBUG_KEY_LINES, tuple(pages[-1].split('\n')))
        for page in pages[:-1]:
            for line in DEBUG_KEY_LINES:
                self.assertNotIn(line, page)

    def test_pages_fit_the_dialog_box(self):
        tile_size = test_config['TILE_SIZE']
        # from the text's left edge (tile 3) to inside the right border (half a tile in from tile 14)
        max_row_width = (2 + 12) * tile_size - tile_size // 2 - 3 * tile_size
        directories = Directories(test_config)
        for language in ('English', 'Korean'):
            for page in self.help_pages(debug_keys=True, language=language):
                rows = wrapped_rows(page)
                with self.subTest(language=language, page=page):
                    self.assertLessEqual(len(rows), MAX_ROWS_PER_PAGE)
                    current_font = set_font_by_ascii_chars(rows, 16, None, directories)
                    for row in rows:
                        self.assertLessEqual(current_font.size(row)[0], max_row_width, row)

    def test_korean_header_is_translated(self):
        self.assertEqual("컨트롤:", self.help_pages(debug_keys=False, language='Korean')[0].split('\n')[0])
