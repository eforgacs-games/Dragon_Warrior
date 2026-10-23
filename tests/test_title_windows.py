"""The title screen's windows (src/title_windows.py) against the 18 NES screenshots they replace, 0 differing pixels at
every scale (see tests/nes_screen_diff.py), in Korean, and the NES flow they're drawn in: BEGIN A NEW QUEST lists only
the open logs (ShowOpenLogs), and CONTINUE A QUEST with one log shows its hero's name (ShowUsedLogs)."""
import builtins
import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import Surface

from src.color import BLACK, WHITE
from src.common import set_gettext_language
from src.config.test_config import test_config
from src.directories import Directories
from src.name_entry import NameEntry, render_name_entry_screen
from src.title_menu import BACK_TO_TITLE_MENU
from src.title_windows import TitleWindow, draw_title_windows, title_menu_layout, title_translate
from src.window_renderer import NES_TILE, glyph_tile, tile_surface
from src.windows import (ADVENTURE_LOG_123_LAYOUT, ADVENTURE_LOG_WINDOW_1, ADVENTURE_LOG_WINDOW_2,
                         CONTINUE_CHANGE_ERASE_LAYOUT, FULL_MENU_LAYOUT, NEW_QUEST_LAYOUT, open_logs_layout,
                         used_logs_layout)
from tests.nes_screen_diff import compare_with_screenshot, count_differing_pixels, load_screenshot
from tests.test_options_screen import B, DOWN, ENTER, OptionsTestCase, presses

SCALES = (1, 2, 3)
DIFF_DIR = os.path.join(tempfile.gettempdir(), 'dragon_warrior_screen_diffs')
MAIN_MENU = os.path.join(Directories(test_config).IMAGES_DIR, 'menus', 'main_menu')
ONE_LOG = used_logs_layout(((1, ''),))


def screenshot(path: str) -> str:
    return os.path.join(MAIN_MENU, path)


# Each screenshot and the windows that draw it, bottom to top: (layout, cursor entry, cursor visible). An
# "-1_unselected" screenshot is the cursor in the "off" half of its blink.
SCREENSHOTS: dict[str, list[TitleWindow]] = {
    # NewQuestDat, no log used
    'empty_log/0_begin_quest.png': [(NEW_QUEST_LAYOUT, 0, True)],
    'empty_log/-1_unselected.png': [(NEW_QUEST_LAYOUT, 0, False)],
    # FullMenuDat, some logs used
    **{f'partially_full_log/{entry}.png': [(FULL_MENU_LAYOUT, index, True)] for index, entry in enumerate(
        ('0_continue_quest', '1_change_message_speed', '2_begin_new_quest', '3_copy_quest', '4_erase_quest'))},
    'partially_full_log/-1_unselected.png': [(FULL_MENU_LAYOUT, 0, False)],
    # ContChngErsDat, every log used
    **{f'full_log/{entry}.png': [(CONTINUE_CHANGE_ERASE_LAYOUT, index, True)] for index, entry in enumerate(
        ('0_continue_quest', '1_change_message_speed', '2_erase_quest'))},
    'full_log/-1_unselected.png': [(CONTINUE_CHANGE_ERASE_LAYOUT, 0, False)],
    # BEGIN A NEW QUEST with every log open: LogList123Dat1 over NewQuestDat, whose arrow stays on
    **{f'empty_log/adventure_log/{log - 1}_adventure_log_{log}.png':
       [(NEW_QUEST_LAYOUT, 0, True), (ADVENTURE_LOG_123_LAYOUT, log - 1, True)] for log in (1, 2, 3)},
    'empty_log/adventure_log/-1_unselected.png': [(NEW_QUEST_LAYOUT, 0, True), (ADVENTURE_LOG_123_LAYOUT, 0, False)],
    # CONTINUE A QUEST with log 1 used: LogList1Dat2 over FullMenuDat. The screenshot's name is blank (the game drew
    # the name over it)
    'partially_full_log/one_adventure_log/0_adventure_log_1.png': [(FULL_MENU_LAYOUT, 0, True), (ONE_LOG, 0, True)],
    'partially_full_log/one_adventure_log/-1_unselected.png': [(FULL_MENU_LAYOUT, 0, True), (ONE_LOG, 0, False)],
}


def config_at(scale: int) -> dict:
    return {**test_config, 'TILE_SIZE': 16 * scale, 'NO_BLIT': False}


def english(text: str) -> str:
    return text


def title_screen(windows: list[TitleWindow], scale: int, translate=english) -> Surface:
    screen = Surface((256 * scale, 240 * scale))
    screen.fill(BLACK)
    draw_title_windows(screen, windows, config_at(scale), translate)
    return screen


class TestTitleWindowsMatchTheScreenshots(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_every_screenshot_at_every_scale(self):
        self.assertEqual(18, len(SCREENSHOTS))
        for path, windows in SCREENSHOTS.items():
            for scale in SCALES:
                with self.subTest(screenshot=path, scale=scale):
                    result = compare_with_screenshot(title_screen(windows, scale), screenshot(path), scale,
                                                     diff_dir=DIFF_DIR, name=path.replace('/', '_') + f'_{scale}')
                    self.assertEqual(0, result.differing_pixels, result)

    def test_the_hero_s_name_is_in_the_nes_font(self):
        # LogList1Dat2 with a name: the screenshot, with the first 4 letters' tiles after the ":" (WndLwr4Saved)
        for scale in SCALES:
            with self.subTest(scale=scale):
                generated = title_screen([(FULL_MENU_LAYOUT, 0, True), (used_logs_layout(((1, 'Erdrick'),)), 0, True)],
                                         scale)
                expected = load_screenshot(screenshot('partially_full_log/one_adventure_log/0_adventure_log_1.png'),
                                           scale)
                tile = NES_TILE * scale
                # the window is at block (3, 6); the name starts at its tile column 18, on its tile row 2
                for offset, letter in enumerate('Erdr'):
                    expected.blit(tile_surface(glyph_tile(letter), WHITE, scale),
                                  ((3 * 2 + 18 + offset) * tile, (6 * 2 + 2) * tile))
                self.assertEqual(0, count_differing_pixels(generated, expected))


class TestLogWindowLayouts(TestCase):
    """The LogList??Dat1 and LogList??Dat2 windows ShowOpenLogs and ShowUsedLogs pick from: as high as their logs."""

    def test_open_logs(self):
        layout = open_logs_layout((1, 3))
        self.assertEqual(ADVENTURE_LOG_WINDOW_1._replace(height=3), layout.window)
        self.assertEqual(['ADVENTURE LOG 1', 'ADVENTURE LOG 3'], [text.text for text in layout.texts])
        self.assertEqual(((1, 2), (1, 4)), layout.cursor_tiles)

    def test_used_logs_show_4_letters_of_the_name(self):
        layout = used_logs_layout(((1, 'Erdrick'), (2, 'Ed'), (3, 'Loto')))
        self.assertEqual(ADVENTURE_LOG_WINDOW_2, layout.window)
        self.assertEqual(['ADVENTURE LOG 1:Erdr', 'ADVENTURE LOG 2:Ed  ', 'ADVENTURE LOG 3:Loto'],
                         [text.text for text in layout.texts])

    def test_title_menu_by_logs_used(self):
        self.assertEqual([NEW_QUEST_LAYOUT, FULL_MENU_LAYOUT, FULL_MENU_LAYOUT, CONTINUE_CHANGE_ERASE_LAYOUT],
                         [title_menu_layout(used) for used in range(4)])


class TestKoreanTitleWindows(TestCase):
    """The NES font has no Korean: translated, each line is drawn as text at its NES tile (src/translated_window.py)."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        had_builtin, old_builtin = hasattr(builtins, '_'), getattr(builtins, '_', None)
        self.translate = title_translate(set_gettext_language('Korean'))
        self.addCleanup(self.restore_builtin, had_builtin, old_builtin)

    @staticmethod
    def restore_builtin(had_builtin, old_builtin):
        if had_builtin:
            builtins._ = old_builtin  # type: ignore[attr-defined]
        elif hasattr(builtins, '_'):
            del builtins._  # type: ignore[attr-defined]

    def drawn(self, windows):
        with patch('src.translated_window.draw_text') as draw_text:
            title_screen(windows, 2, self.translate)
        return [call.args[0] for call in draw_text.call_args_list]

    def test_title_menus(self):
        self.assertEqual(['모험을 계속한다', '표시 속도를 바꾼다', '새로운 모험을 시작한다', '모험의 서를 복사한다',
                          '모험의 서를 지운다'], self.drawn([(FULL_MENU_LAYOUT, 0, True)]))
        self.assertEqual(['새로운 모험을 시작한다'], self.drawn([(NEW_QUEST_LAYOUT, 0, True)]))
        self.assertEqual(['모험을 계속한다', '표시 속도를 바꾼다', '모험의 서를 지운다'],
                         self.drawn([(CONTINUE_CHANGE_ERASE_LAYOUT, 0, True)]))

    def test_log_windows_keep_the_number_and_the_name(self):
        self.assertEqual(['모험의 서 2', '모험의 서 3'], self.drawn([(open_logs_layout((2, 3)), 0, True)]))
        # the hero's name is never translated, even one that is a catalog message
        self.assertEqual(['모험의 서 1:YES ', '모험의 서 3:Erdr'],
                         self.drawn([(used_logs_layout(((1, 'YES'), (3, 'Erdrick'))), 0, True)]))

    def test_english_is_drawn_in_the_nes_font(self):
        english_translate = title_translate(set_gettext_language('English'))
        with patch('src.translated_window.draw_text') as draw_text:
            title_screen([(FULL_MENU_LAYOUT, 0, True), (used_logs_layout(((1, 'Erdrick'),)), 0, True)], 2,
                         english_translate)
        draw_text.assert_not_called()

    def test_a_name_with_no_nes_tile_is_drawn_as_text(self):
        with patch('src.translated_window.draw_text') as draw_text:
            title_screen([(used_logs_layout(((1, '용사'),)), 0, True)], 2, english)
        self.assertEqual(['ADVENTURE LOG 1:용사  '], [call.args[0] for call in draw_text.call_args_list])


class TestTitleMenuFlow(OptionsTestCase):
    """The windows the title menu opens, as TitleMenu runs them, with saves in a temporary folder."""

    def setUp(self):
        super().setUp()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.game.directories.save_dir = self.tmp_dir.name

    def write_saves(self, slots):
        for slot in (1, 2, 3):
            path = os.path.join(self.tmp_dir.name, f'save_slot_{slot}.json')
            if slot in slots:
                with open(path, 'w') as save_file:
                    json.dump({'Name': f'Hero{slot}', 'Experience': 0}, save_file)
            elif os.path.exists(path):
                os.remove(path)

    def test_begin_a_new_quest_lists_only_the_open_logs(self):
        # Logs 1 and 3 used: ShowOpenLogs shows LogList2Dat1, so A on its only entry is log 2, never log 1
        self.write_saves((1, 3))
        with patch.object(self.game.game_functions, 'main_menu_selection', return_value=0) as selection:
            log_window = self.game.title_menu.select_adventure_log(self.game.screen)
        self.assertEqual(2, self.game.player.adventure_log)
        self.assertEqual(open_logs_layout((2,)), selection.call_args.args[2])
        # over FullMenuDat, its arrow held on BEGIN A NEW QUEST
        self.assertEqual([(FULL_MENU_LAYOUT, 2)], selection.call_args.kwargs['below'])
        self.assertEqual((open_logs_layout((2,)), 0), log_window)

    def test_begin_a_new_quest_with_the_keys(self):
        # Log 1 used: logs 2 and 3 are listed; down and A is log 3
        self.write_saves((1,))
        with patch('src.selection.event.get', side_effect=presses(DOWN, ENTER)):
            self.assertEqual((open_logs_layout((2, 3)), 1), self.game.title_menu.select_adventure_log(self.game.screen))
        self.assertEqual(3, self.game.player.adventure_log)

    def test_b_in_the_open_logs_window_goes_back(self):
        self.write_saves(())
        with patch('src.selection.event.get', side_effect=presses(B)):
            self.assertIs(BACK_TO_TITLE_MENU, self.game.title_menu.select_adventure_log(self.game.screen))

    def test_the_name_entry_draws_the_open_logs_window_behind_it(self):
        self.write_saves((1,))
        with patch.object(self.game.title_menu, 'select_adventure_log', return_value=(open_logs_layout((2, 3)), 1)), \
                patch('src.title_menu.NameSelection') as name_selection, \
                patch.object(self.game.title_menu, 'choose_new_quest_options'), \
                patch.object(self.game, 'start_at_throne_room'):
            name_selection.return_value.select_name.return_value = 'Ed'
            self.game.title_menu.begin_new_quest()
        self.assertEqual((open_logs_layout((2, 3)), 1), name_selection.call_args.args[1])

    def test_continue_with_one_log_shows_its_hero(self):
        # Log 3 only: LogList3Dat2 with its hero's name, over FullMenuDat with the arrow held on CONTINUE A QUEST
        self.write_saves((3,))
        self.game.title_menu.save_dir_contents = self.game.title_menu.save_files()
        with patch.object(self.game.game_functions, 'main_menu_selection', return_value=0) as selection, \
                patch.object(self.game, 'load_game') as load_game:
            self.game.title_menu.continue_quest()
        self.assertEqual(used_logs_layout(((3, 'Hero3'),)), selection.call_args.args[2])
        self.assertEqual([(FULL_MENU_LAYOUT, 0)], selection.call_args.kwargs['below'])
        self.assertEqual('Hero3', load_game.call_args.args[0]['Name'])
        self.assertEqual(3, self.game.player.adventure_log)

    def test_b_in_the_one_log_window_goes_back(self):
        self.write_saves((2,))
        self.game.title_menu.save_dir_contents = self.game.title_menu.save_files()
        with patch('src.selection.event.get', side_effect=presses(B)), \
                patch.object(self.game, 'load_game') as load_game:
            self.assertIs(BACK_TO_TITLE_MENU, self.game.title_menu.continue_quest())
        load_game.assert_not_called()

    def test_the_windows_over_the_title_menu_keep_its_arrow(self):
        # CHANGE MESSAGE SPEED's log window opens over FullMenuDat, its arrow on CHANGE MESSAGE SPEED
        self.write_saves((1,))
        self.game.title_menu.save_dir_contents = self.game.title_menu.save_files()
        with patch('src.title_menu.draw_title_windows') as draw:
            self.game.title_menu.title_menu_background(1)(self.game.screen)
        self.assertEqual([(FULL_MENU_LAYOUT, 1, True)], draw.call_args.args[1])


class TestNameEntryBackground(TestCase):
    """The open logs window stays on screen behind the name entry; only LogList123Dat1's last line shows below
    AlphabetDat, so a shorter window is hidden."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    @staticmethod
    def last_log_line(log_window) -> bytes:
        # LogList123Dat1's third line: NES tile row 24 (block row 9, its tile row 6)
        screen = render_name_entry_screen(NameEntry(), WHITE, 1, None, log_window)
        return pygame.image.tobytes(screen.subsurface((0, 24 * NES_TILE, 256, 2 * NES_TILE)), 'RGB')

    def test_shorter_open_logs_windows_are_hidden(self):
        black = bytes(256 * 2 * NES_TILE * 3)
        self.assertNotEqual(black, self.last_log_line((ADVENTURE_LOG_123_LAYOUT, None)))
        for logs in ((1,), (2, 3), (1, 3)):
            with self.subTest(logs=logs):
                self.assertEqual(black, self.last_log_line((open_logs_layout(logs), 0)))

    def test_log_3_chosen_keeps_its_arrow(self):
        self.assertNotEqual(self.last_log_line((ADVENTURE_LOG_123_LAYOUT, None)),
                            self.last_log_line((ADVENTURE_LOG_123_LAYOUT, 2)))
        self.assertEqual(self.last_log_line((ADVENTURE_LOG_123_LAYOUT, None)),
                         self.last_log_line((ADVENTURE_LOG_123_LAYOUT, 0)))
