"""Every text path draws j, k, p, t and the apostrophe as their NES font tiles (NES_GLYPHS, and the font's ’ for the
apostrophe: src/window_renderer.py glyph_tile), pixel for pixel, in the text color and at every scale; dragon-quest.ttf
draws those five differently. The other characters, and Korean text (unifont), are drawn exactly as before."""
import string
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import Rect, Surface, font

from src.adventure_log import AdventureLogOverlay, OverlayText
from src.color import BLACK, RED, WHITE
from src.config.test_config import test_config
from src.directories import Directories
from src.text import NESFont, draw_text, set_font_by_ascii_chars
from src.window_renderer import NES_GLYPHS, NES_TILE, glyph_tile, tile_surface
from tests.nes_screen_diff import count_differing_pixels

SCALES = (1, 2, 3)
COLORS = (WHITE, RED)
FIVE = "jkpt'"
# A dialog line with all five
SAMPLE = "Erdrick's pet jumped."


def text_config(scale: int = 2) -> dict:
    return {**test_config, 'SCALE': scale, 'TILE_SIZE': 16 * scale, 'NO_BLIT': False, 'RENDER_TEXT': True,
            'NO_WAIT': True, 'SOUND_ENABLED': False, 'MUSIC_ENABLED': False}


class GlyphAssertions(TestCase):

    def assert_nes_tiles(self, surface: Surface, text: str, left: int, top: int, scale: int, color: tuple):
        """Each character of text, from (left, top) one tile after another, is its NES tile (only the five checked
        here are compared, plus the characters around them)."""
        tile = NES_TILE * scale
        for index, character in enumerate(text):
            if character == ' ':
                continue
            with self.subTest(character=character, index=index, scale=scale, color=color):
                drawn = surface.subsurface(Rect(left + index * tile, top, tile, tile))
                expected = tile_surface(glyph_tile(character), color, scale)
                self.assertEqual(0, count_differing_pixels(drawn, expected))


class TestNESFont(GlyphAssertions):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.directories = Directories(test_config)

    def test_the_five_are_nes_tiles_at_every_scale_and_color(self):
        for scale in SCALES:
            nes_font = NESFont(self.directories.DRAGON_QUEST_FONT_PATH, NES_TILE * scale)
            for color in COLORS:
                for antialias in (True, False):
                    for background in (None, BLACK):
                        rendered = nes_font.render(FIVE + ' ' + SAMPLE, antialias, color, background)
                        on_black = Surface(rendered.get_size())
                        on_black.blit(rendered, (0, 0))
                        # the tile is the line's rows scale to scale * 9 (a blank row above and below)
                        self.assert_nes_tiles(on_black, FIVE + ' ' + SAMPLE, 0, scale, scale, color)

    def test_every_other_character_is_drawn_as_before(self):
        others = ''.join(c for c in string.printable.strip() if c not in FIVE) + '’'
        for scale in SCALES:
            size = NES_TILE * scale
            with self.subTest(scale=scale):
                plain = font.Font(self.directories.DRAGON_QUEST_FONT_PATH, size).render(others, True, WHITE, BLACK)
                nes = NESFont(self.directories.DRAGON_QUEST_FONT_PATH, size).render(others, True, WHITE, BLACK)
                self.assertEqual(0, count_differing_pixels(nes, plain))

    def test_the_apostrophe_is_the_fonts_right_quote(self):
        # the NES has one apostrophe; the font's ' is a straight one (src/window_renderer.py)
        self.assertNotIn("'", NES_GLYPHS)
        nes_font = NESFont(self.directories.DRAGON_QUEST_FONT_PATH, 16)
        self.assertEqual(0, count_differing_pixels(nes_font.render("'", True, WHITE, BLACK),
                                                   nes_font.render('’', True, WHITE, BLACK)))


class TestDrawText(GlyphAssertions):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def draw(self, scale: int, color: tuple, letter_by_letter: bool) -> tuple[Surface, int, int]:
        screen = Surface((400 * scale, 40 * scale))
        screen.fill(BLACK)
        left, middle = 8 * scale, 20 * scale
        with patch('src.text.display.update'):
            draw_text(SAMPLE + ' ' + FIVE, left, middle, screen, text_config(scale), color=color, size=8 * scale,
                      letter_by_letter=letter_by_letter, disable_sound=True, text_wrap_length=40)
        # draw_text centres the line (10 NES pixels high) on y: the tile starts 4 NES pixels above it
        return screen, left, middle - 4 * scale

    def test_draw_text(self):
        for scale in SCALES:
            for color in COLORS:
                screen, left, top = self.draw(scale, color, letter_by_letter=False)
                self.assert_nes_tiles(screen, SAMPLE + ' ' + FIVE, left, top, scale, color)

    def test_draw_text_letter_by_letter(self):
        for scale in SCALES:
            for color in COLORS:
                screen, left, top = self.draw(scale, color, letter_by_letter=True)
                self.assert_nes_tiles(screen, SAMPLE + ' ' + FIVE, left, top, scale, color)


class TestAdventureLogOverlay(GlyphAssertions):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_overlay_text(self):
        for scale in SCALES:
            screen = Surface((256 * scale, 32 * scale))
            screen.fill(BLACK)
            AdventureLogOverlay([OverlayText(FIVE, 2, 1)], text_config(scale))(screen)
            self.assert_nes_tiles(screen, FIVE, 2 * 8 * scale, 8 * scale, scale, WHITE)


class TestDialogBox(GlyphAssertions):
    """CommandMenu's dialog window (src/dialog_box.py's buffer, drawn by draw_dialog_text), at SCALE 2."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self) -> None:
        from src.game import Game
        from tests.mock_map import MockMap
        self.saved_config = dict(test_config)
        test_config.update(NO_WAIT=True, RENDER_TEXT=True, NO_BLIT=False)
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])
        self.cmd_menu = self.game.cmd_menu
        self.cmd_menu.screen.fill(BLACK)

    def tearDown(self) -> None:
        test_config.clear()
        test_config.update(self.saved_config)

    def assert_dialog_row(self, text: str, color: tuple, row: int = 0):
        cells = self.cmd_menu.dialog_cell_rect(row)
        self.assert_nes_tiles(self.cmd_menu.screen, text, cells.left, cells.top, 2, color)

    def test_dialog_text(self):
        for color in COLORS:
            self.game.color = color
            self.cmd_menu.draw_dialog_text(SAMPLE, self.cmd_menu.dialog_cell_rect(0), update=False)
            self.assert_dialog_row(SAMPLE, color)

    def test_dialog_row_letter_by_letter(self):
        # while a row is printed, it is drawn up to the column printed so far
        for color in COLORS:
            self.game.color = color
            self.cmd_menu.dialog_buffer.rows[0][:len(SAMPLE)] = list(SAMPLE)
            for column in range(1, len(SAMPLE) + 1):
                self.cmd_menu.draw_dialog_row(0, up_to_column=column, update=False)
                self.assert_dialog_row(SAMPLE[:column], color)

    def test_show_line_in_dialog_box(self):
        with patch.object(self.cmd_menu, 'window_drop_down_effect'), \
                patch.object(self.cmd_menu, 'window_drop_up_effect'):
            self.cmd_menu.show_line_in_dialog_box(SAMPLE, add_quotes=False, skip_text=True, hide_arrow=True,
                                                  disable_sound=True)
        self.assert_dialog_row(SAMPLE, WHITE)


class TestKorean(TestCase):
    """Korean text is drawn in unifont (set_font_by_ascii_chars picks the font by script), untouched."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.directories = Directories(test_config)

    def test_korean_text_uses_plain_unifont(self):
        text = "용사 jkpt'의 펫"
        current_font = set_font_by_ascii_chars([text], 16, None, self.directories)
        self.assertNotIsInstance(current_font, NESFont)
        unifont = font.Font(self.directories.UNIFONT_PATH, 16)
        unifont.bold = True
        self.assertEqual(0, count_differing_pixels(current_font.render(text, True, WHITE, BLACK),
                                                   unifont.render(text, True, WHITE, BLACK)))

    def test_ascii_text_uses_the_nes_font(self):
        self.assertIsInstance(set_font_by_ascii_chars([SAMPLE], 16, None, self.directories), NESFont)
        self.assertIsInstance(set_font_by_ascii_chars([SAMPLE], 16, self.directories.DRAGON_QUEST_FONT_PATH,
                                                      self.directories), NESFont)
        self.assertNotIsInstance(set_font_by_ascii_chars([SAMPLE], 16, self.directories.SMB_FONT_PATH,
                                                         self.directories), NESFont)
