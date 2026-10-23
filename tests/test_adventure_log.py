import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame

from src.adventure_log import (AdventureLogOverlay, OverlayText, adventure_log_overlay_texts,
                               log_name_tiles, read_save_name, save_slot_number)
from src.color import WHITE
from src.config.test_config import test_config
from src.directories import Directories
from src.game_functions import blit_scaled_image


def write_save(directory: str, slot: int, contents) -> str:
    save_path = os.path.join(directory, f'save_slot_{slot}.json')
    with open(save_path, 'w') as save_file:
        if isinstance(contents, str):
            save_file.write(contents)
        else:
            json.dump(contents, save_file)
    return save_path


class TestLogNameTiles(TestCase):
    """Bank01 WndLwr4Saved shows the first 4 letters; WndEnterName pads unused letters with blank tiles."""

    def test_long_name_is_cut_to_four_letters(self):
        self.assertEqual('ERDR', log_name_tiles('ERDRICK'))
        self.assertEqual('ABCD', log_name_tiles('ABCDEFGH'))

    def test_four_letter_name_is_unchanged(self):
        self.assertEqual('Loto', log_name_tiles('Loto'))

    def test_short_name_is_padded_with_blanks(self):
        self.assertEqual('Ed  ', log_name_tiles('Ed'))
        self.assertEqual('A   ', log_name_tiles('A'))
        self.assertEqual('    ', log_name_tiles(''))


class TestReadSave(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def test_reads_name(self):
        self.assertEqual('ERDRICK', read_save_name(write_save(self.tmp_dir.name, 1, {'Name': 'ERDRICK'})))

    def test_missing_file(self):
        self.assertIsNone(read_save_name(os.path.join(self.tmp_dir.name, 'save_slot_1.json')))

    def test_unreadable_files(self):
        for contents in ('{not json', '', '["a list"]', {'Gold': 5}, {'Name': None}, {'Name': 3}):
            with self.subTest(contents=contents):
                self.assertIsNone(read_save_name(write_save(self.tmp_dir.name, 1, contents)))

    def test_slot_number(self):
        self.assertEqual(1, save_slot_number('/x/save_slot_1.json'))
        self.assertEqual(3, save_slot_number('save_slot_3.json'))
        self.assertIsNone(save_slot_number('/x/notes.txt'))


class TestOverlayTexts(TestCase):
    """LogList1Dat2: " ADVENTURE LOG 1:" then the name, on NES tile row 14; the name starts at column 24."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def test_log_1_draws_only_the_name(self):
        save_path = write_save(self.tmp_dir.name, 1, {'Name': 'ERDRICK'})
        self.assertEqual([OverlayText('ERDR', 24, 14)], adventure_log_overlay_texts(save_path))

    def test_short_name_is_padded(self):
        save_path = write_save(self.tmp_dir.name, 1, {'Name': 'Ed'})
        self.assertEqual([OverlayText('Ed  ', 24, 14)], adventure_log_overlay_texts(save_path))

    def test_other_log_redraws_the_number(self):
        # the screenshot says "ADVENTURE LOG 1:"; LogList2Dat2 says "ADVENTURE LOG 2:"
        save_path = write_save(self.tmp_dir.name, 2, {'Name': 'Loto'})
        self.assertEqual([OverlayText('2', 22, 14), OverlayText('Loto', 24, 14)],
                         adventure_log_overlay_texts(save_path))

    def test_later_lines_are_one_block_lower(self):
        save_path = write_save(self.tmp_dir.name, 3, {'Name': 'Loto'})
        self.assertEqual([OverlayText('Loto', 24, 18)],
                         adventure_log_overlay_texts(save_path, line=2, screenshot_log_number=3))

    def test_no_save_draws_nothing(self):
        self.assertEqual([], adventure_log_overlay_texts(os.path.join(self.tmp_dir.name, 'save_slot_1.json')))
        self.assertEqual([], adventure_log_overlay_texts(write_save(self.tmp_dir.name, 1, '{broken')))


class TestAdventureLogOverlay(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.config = dict(test_config, RENDER_TEXT=True, NO_BLIT=False)
        cls.screen = pygame.display.set_mode((256 * test_config['SCALE'], 240 * test_config['SCALE']))

    def test_draws_at_the_nes_tile(self):
        overlay = AdventureLogOverlay([OverlayText('ERDR', 24, 14)], self.config)
        with patch('src.adventure_log.blit_text_to_screen') as mock_blit:
            overlay(self.screen)
        # an NES tile is 16 screen pixels at SCALE 2: left edge of column 24, middle of row 14
        mock_blit.assert_called_once_with('left', WHITE, overlay._font, self.screen, 'ERDR', 384, 232, True)

    def test_nothing_to_draw(self):
        with patch('src.adventure_log.blit_text_to_screen') as mock_blit:
            AdventureLogOverlay([], self.config)(self.screen)
        mock_blit.assert_not_called()

    def test_letters_sit_on_the_screenshots_tile_grid(self):
        """Redrawing the screenshot's own "ADVENTURE LOG 1:" (columns 8-23, row 14) lights exactly the same pixels,
        so the name uses the same glyphs, size and grid."""
        directories = Directories(self.config)
        blit_scaled_image(directories.one_adventure_log_0, self.screen)
        before = self.screen.copy()
        AdventureLogOverlay([OverlayText('ADVENTURE LOG 1:', 8, 14)], self.config)(self.screen)

        def lit(surface, x, y):
            return sum(surface.get_at((x, y))[:3]) > 300

        # the whole adventure log window: NES tile rows 12-15
        mismatched = [(x, y) for x in range(self.screen.get_width()) for y in range(16 * 12, 16 * 16)
                      if lit(before, x, y) != lit(self.screen, x, y)]
        self.assertEqual([], mismatched)

    def test_blit_scaled_image_draws_the_overlay_before_updating(self):
        calls = []
        overlay = MagicMock(side_effect=lambda screen: calls.append('overlay'))
        with patch('src.game_functions.display.update', side_effect=lambda rect: calls.append('update')):
            blit_scaled_image(Directories(self.config).one_adventure_log_0, self.screen, overlay=overlay)
        overlay.assert_called_once_with(self.screen)
        self.assertEqual(['overlay', 'update'], calls)
