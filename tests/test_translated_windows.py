"""Every translation (each catalog language in src/languages.py) fits the windows it's drawn in: the generated windows
drawn translated (src/translated_window.py), the status window's equipment, the options overlay, the CONTROLS screen and
the message log. Translated text is drawn in Unifont, where a Hangul syllable, a kana or a kanji is one NES tile wide
and an ASCII character half of one."""
import builtins
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.common import set_gettext_language
from src.config.test_config import test_config
from src.directories import Directories
from src.game import Game
from src.items import armor, shields, weapons
from src.languages import CATALOG_LANGUAGES, Language
from src.options_overlay import OPTION_PAGES, OPTION_ROWS, OPTIONS_WINDOW, VALUE_COLUMN, options_layout
from src.text import WRAP_LENGTH, set_font_by_ascii_chars
from src.translated_window import draw_translated_window, layout_texts
from src.windows import COMBAT_COMMAND_LAYOUT, COMMAND_LAYOUT, STATUS_LAYOUT, STATUS_WINDOW, TITLE_MENU_LAYOUTS, \
    TITLE_MENU_LAYOUTS_WITH_AUTOSAVE, YES_NO_LAYOUT, WindowLayout

NES_TILE = test_config['TILE_SIZE'] / 2  # screen pixels
# The generated windows drawn translated, and whether their text lines up on its right edge (the status labels)
TRANSLATED_LAYOUTS = ((COMMAND_LAYOUT, False), (COMBAT_COMMAND_LAYOUT, False), (STATUS_LAYOUT, True),
                      (YES_NO_LAYOUT, False), *((layout, False) for layout in TITLE_MENU_LAYOUTS),
                      *((layout, False) for layout in TITLE_MENU_LAYOUTS_WITH_AUTOSAVE))
# Where StatusDat puts the weapon, armor and shield (CommandMenu.draw_status_window): from tile column 10
STATUS_EQUIPMENT_COLUMN = 10


class TranslatedTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))
        cls.font = set_font_by_ascii_chars(['設定'], 16, None, Directories(test_config))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        # set_gettext_language installs a catalog's _ into builtins; put things back afterwards
        had_builtin, old_builtin = hasattr(builtins, '_'), getattr(builtins, '_', None)
        self.addCleanup(self.restore_builtin, had_builtin, old_builtin)

    @staticmethod
    def restore_builtin(had_builtin, old_builtin):
        if had_builtin:
            builtins._ = old_builtin  # type: ignore[attr-defined]
        elif hasattr(builtins, '_'):
            del builtins._  # type: ignore[attr-defined]

    def width(self, text: str) -> float:
        """How many NES tiles the text takes in Unifont."""
        return self.font.size(text)[0] / NES_TILE

    def languages(self):
        """(language, its gettext function) for each translation."""
        return [(language, set_gettext_language(language.name)) for language in CATALOG_LANGUAGES]


class TestGeneratedWindows(TranslatedTestCase):

    def assert_fits(self, layout: WindowLayout, right_aligned: bool, language: Language, translate) -> None:
        """Each text inside the window's borders, and ending before the cursor of the next text on its row."""
        right_border = layout.window.width * 2 - 1
        for text in layout_texts(layout):
            translated = translate(text.text)
            width = self.width(translated)
            end = text.column + len(text.text) if right_aligned else text.column + width
            start = end - width
            next_cursor = min((other.column - 1 for other in layout.texts
                               if other.row == text.row and other.column > text.column), default=right_border)
            with self.subTest(language=language.name, text=translated):
                self.assertGreaterEqual(start, 1)
                self.assertLessEqual(end, next_cursor if text.row else right_border)

    def test_every_layout_fits(self):
        for language, translate in self.languages():
            for layout, right_aligned in TRANSLATED_LAYOUTS:
                self.assert_fits(layout, right_aligned, language, translate)

    def test_status_window_equipment_fits(self):
        right_border = STATUS_WINDOW.width * 2 - 1
        for language, translate in self.languages():
            for name in (*weapons, *armor, *shields):
                with self.subTest(language=language.name, name=translate(name)):
                    self.assertLessEqual(STATUS_EQUIPMENT_COLUMN + self.width(translate(name)), right_border)


class TestOptionsOverlay(TranslatedTestCase):

    def setUp(self):
        super().setUp()
        with patch('src.game.SCALED'):
            self.game = Game(test_config)

    def overlay_texts(self, config, page, translate):
        with patch('src.translated_window.draw_text') as draw_text:
            draw_translated_window(self.game.screen, options_layout(config, page), (255, 255, 255), config,
                                   translate, cursor_index=0)
        return [(call.args[0], call.args[1] / NES_TILE, call.args[2] / NES_TILE)
                for call in draw_text.call_args_list]

    def test_text_fits(self):
        # Each label ends before its value starts, and each value inside the window's right border, in the window's
        # one font (Unifont), with every value of every row, on every page
        right_border = (OPTIONS_WINDOW.x + OPTIONS_WINDOW.width) * 2 - 1
        title_end = OPTIONS_WINDOW.x * 2 + OPTIONS_WINDOW.width * 2 - 1
        for language, translate in self.languages():
            for choice in range(3):
                # NO_BLIT off, whatever another test left in test_config: draw_translated_window draws nothing with it
                config = {**self.game.game_state.config, 'LANGUAGE': language.name, 'NO_BLIT': False,
                          **{row.config_key: row.values[choice % len(row.values)] for row in OPTION_ROWS}}
                for page in range(len(OPTION_PAGES)):
                    title, *texts = self.overlay_texts(config, page, translate)
                    with self.subTest(language=language.name, text=title[0]):
                        self.assertLessEqual(title[1] + self.width(title[0]), title_end)
                    for text, column, row in texts:
                        end = OPTIONS_WINDOW.x * 2 + (VALUE_COLUMN - 1 if column < VALUE_COLUMN else right_border)
                        with self.subTest(language=language.name, text=text):
                            self.assertLessEqual(column + self.width(text), end)


class TestControlsScreen(TranslatedTestCase):

    def layouts(self, translate):
        """The CONTROLS window scrolled to each place, and with each bottom line, translated."""
        from src.controls import ACTIONS, current_controls
        from src.controls_screen import CHANGED_TOO, NEEDS_A_KEY, VISIBLE_ROWS, Cell, controls_layout, screen_texts
        layouts = [controls_layout(current_controls(), Cell(top, 0), top, '')
                   for top in range(len(ACTIONS) + 2 - VISIBLE_ROWS)]
        for hint in screen_texts():
            translated = translate(hint)
            if hint in (CHANGED_TOO, NEEDS_A_KEY):
                longest = max((translate(action.label) for action in ACTIONS), key=len)
                translated = translated.format(longest)
            layouts.append(controls_layout(current_controls(), Cell(0, 0), 0, translated))
        return layouts

    def test_text_fits(self):
        # Each label ends before KEY 1's cursor, each cell before the next cell's cursor, and the rest (the reset
        # row, the bottom line, the PAD cell) inside the right border
        from src.controls_screen import CELL_CURSOR_COLUMNS, CONTROLS_WINDOW, HINT_ROW, RESET_LABEL
        right_border = (CONTROLS_WINDOW.x + CONTROLS_WINDOW.width) * 2 - 1
        for language, translate in self.languages():
            for layout in self.layouts(translate):
                for text in layout.texts:
                    translated = translate(text.text)
                    spans_the_row = text.row == HINT_ROW or text.text == RESET_LABEL
                    end = right_border if spans_the_row else next(
                        (column for column in CELL_CURSOR_COLUMNS if column > text.column), right_border)
                    with self.subTest(language=language.name, text=translated):
                        self.assertLessEqual(text.column + self.width(translated), end)
                        self.assertLessEqual(len(translated), WRAP_LENGTH)  # draw_text would wrap it


class TestMessageLog(TranslatedTestCase):

    def test_text_fits(self):
        # Every line, the title and the bottom line inside the right border
        from src.message_log import LOG_WINDOW, LogEntry, log_layout, log_lines
        right_border = (LOG_WINDOW.x + LOG_WINDOW.width) * 2 - 1
        for language, translate in self.languages():
            entries = [LogEntry(translate("I am Gwaelin, daughter of Lorik.") * 3, 'PRINCESS_GWAELIN'),
                       LogEntry("Thou hast found the Silver Harp. " * 3, 'WISE_MAN')]
            lines = log_lines(entries, translate)
            self.assertTrue(lines[0].startswith(translate('GWAELIN')))
            for layout in (log_layout(lines, 0, translate("UP/DOWN:SCROLL  B:CLOSE")), log_layout([], 0)):
                for text in (layout.title, *layout.texts):
                    translated = translate(text.text)
                    with self.subTest(language=language.name, text=translated):
                        self.assertLessEqual(text.column + self.width(translated), right_border)
