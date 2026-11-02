"""data/fonts/unifont.otf (GNU Unifont), the font the game draws every translation and other non-NES text in, has a
glyph for every character each catalog uses, and comes with its license (data/fonts/OFL-unifont.txt)."""
import os
import unicodedata
from os.path import isfile
from unittest import TestCase

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from fontTools.ttLib import TTFont

from src.catalog import po_path, read_po
from src.languages import CATALOG_LANGUAGES
from src.paths import data_path
from src.text import TextPaths

UNIFONT_PATH = data_path('fonts', 'unifont.otf')
HANGUL_SYLLABLES = range(0xAC00, 0xD7A4)
CJK_UNIFIED_IDEOGRAPHS = range(0x4E00, 0xA000)
HIRAGANA_AND_KATAKANA = range(0x3040, 0x3100)


def catalog_characters(locale_code: str) -> set[str]:
    """Every character of every msgstr in a catalog (the header excepted), but line breaks."""
    return {character
            for msgid, msgstr in read_po(po_path(locale_code)).items() if msgid
            for character in msgstr if character != '\n'}


def missing_glyph_code_point(cmap: dict[int, str]) -> int:
    """A character the font has no glyph for (pygame draws it as the font's .notdef box, "tofu")."""
    return next(code_point for code_point in range(0xE000, 0xF900) if code_point not in cmap)


class TestUnifont(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.font = TTFont(UNIFONT_PATH)
        cls.cmap = cls.font.getBestCmap()

    def test_text_draws_in_this_file(self):
        self.assertEqual(TextPaths.UNIFONT_PATH, UNIFONT_PATH)

    def test_every_catalog_character_has_a_glyph(self):
        for language in CATALOG_LANGUAGES:
            characters = catalog_characters(language.locale_code or '')
            missing = sorted(f'U+{ord(c):04X} {unicodedata.name(c, "?")}' for c in characters
                             if ord(c) not in self.cmap)
            with self.subTest(language=language.name):
                self.assertGreater(len(characters), 300)
                self.assertEqual([], missing)

    def test_pygame_draws_every_catalog_character(self):
        # Each character renders as its own glyph, not as the box drawn for a character the font hasn't got
        pygame.font.init()
        self.addCleanup(pygame.font.quit)
        font = pygame.font.Font(UNIFONT_PATH, 16)

        def picture(character: str) -> bytes:
            return pygame.image.tobytes(font.render(character, False, (255, 255, 255), (0, 0, 0)), 'RGB')
        tofu = picture(chr(missing_glyph_code_point(self.cmap)))
        for language in CATALOG_LANGUAGES:
            drawn_as_tofu = sorted(f'U+{ord(c):04X} {unicodedata.name(c, "?")}'
                                   for c in catalog_characters(language.locale_code or '')
                                   if not c.isspace() and picture(c) == tofu)
            with self.subTest(language=language.name):
                self.assertEqual([], drawn_as_tofu)

    def test_covers_all_hangul_syllables_and_bmp_cjk(self):
        # All of Hangul for Korean text; kana and the CJK ideographs for a Japanese or Chinese translation
        for block in (HANGUL_SYLLABLES, CJK_UNIFIED_IDEOGRAPHS, HIRAGANA_AND_KATAKANA):
            missing = [hex(code_point) for code_point in block if code_point not in self.cmap]
            self.assertEqual([], missing)

    def test_license(self):
        self.assertIn('SIL Open Font License', self.font['name'].getDebugName(13))
        license_path = data_path('fonts', 'OFL-unifont.txt')
        self.assertTrue(isfile(license_path))
        with open(license_path, encoding='utf-8') as license_file:
            self.assertIn('SIL OPEN FONT LICENSE Version 1.1', license_file.read())

    def test_pygame_draws_hangul_on_the_16_pixel_grid(self):
        # Unifont is a 16-pixel bitmap font: at size 16, a line is 16 pixels high and Hangul is 16 pixels wide
        pygame.font.init()
        self.addCleanup(pygame.font.quit)
        font = pygame.font.Font(UNIFONT_PATH, 16)
        self.assertEqual(16, font.get_height())
        self.assertEqual((32, 16), font.size('용사'))
        self.assertEqual((8, 16), font.size('A'))
        self.assertTrue(font.render('용사', True, (255, 255, 255), (0, 0, 0)).get_bounding_rect().width > 0)
