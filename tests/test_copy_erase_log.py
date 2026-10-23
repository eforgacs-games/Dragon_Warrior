"""The title menu's COPY A QUEST and ERASE AN ADVENTURE LOG (NES Bank03 DoCopyGame and DoEraseGame), and B in CONTINUE
A QUEST with one log, driven key by key through the real windows."""
import gettext
import json
import os
import tempfile
from unittest.mock import patch

from pygame import K_ESCAPE, KEYDOWN
from pygame.event import Event

from src.common import set_gettext_language
from src.title_menu import BACK_TO_TITLE_MENU
from src.options_screen import OptionsScreen, erase_log_window, open_log_options, yes_no_options
from src.windows import ADVENTURE_LOG_WINDOW_1, CONTINUE_CHANGE_ERASE_LAYOUT, ERASE_LOG_WINDOW, YES_NO_2_WINDOW
from tests.test_options_screen import B, DOWN, ENTER, OptionsTestCase, presses

ESC = Event(KEYDOWN, key=K_ESCAPE)  # B too (reject_keys, B_BUTTON_KEYS)
COPY = 3  # FullMenuDat: CONTINUE, CHANGE MESSAGE SPEED, BEGIN A NEW QUEST, COPY A QUEST, ERASE AN ADVENTURE LOG
ERASE = 4
CONTINUE = 0  # the first entry of every title menu with a log in it


class TestCopyAndErase(OptionsTestCase):

    def setUp(self):
        super().setUp()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.game.directories.save_dir = self.tmp_dir.name
        # Loto has 7 experience: level 2 (LevelUpTbl)
        self.saves = {1: {'Name': 'Erdrick', 'Experience': 0, 'Gold': 120, 'Inventory': []},
                      2: {'Name': 'Lotoroto', 'Experience': 7, 'Gold': 5, 'Inventory': []}}
        for slot, save in self.saves.items():
            with open(self.save_path(slot), 'w') as save_file:
                json.dump(save, save_file)

    def save_path(self, slot):
        return os.path.join(self.tmp_dir.name, f'save_slot_{slot}.json')

    def no_screenshot_menu(self):
        """The log windows are generated; the old all-three-logs screenshot menu must not open."""
        return patch.object(self.game.game_functions, 'main_menu_selection',
                            side_effect=AssertionError('the all-logs screenshot menu opened'))

    def logs(self):
        """Each log's save, or None for an open log."""
        logs = {}
        for slot in (1, 2, 3):
            try:
                with open(self.save_path(slot)) as save_file:
                    logs[slot] = json.load(save_file)
            except FileNotFoundError:
                logs[slot] = None
        return logs

    def run_title_menu(self, entry, events):
        """Choose `entry` on the title menu, play the events in its windows, then CONTINUE A QUEST: the title menu
        has to come back (WndBackToMain)."""
        with patch.object(self.game.game_functions, 'main_menu_selection', side_effect=[entry, CONTINUE]) \
                as title_menu, patch.object(self.game.title_menu, 'continue_quest') as continue_quest, \
                patch('src.selection.event.get', side_effect=presses(*events)):
            self.game.title_menu.show_main_menu_screen(self.game.screen)
        self.assertEqual(2, title_menu.call_count)
        continue_quest.assert_called_once()

    # COPY A QUEST

    def test_copy_from_a_used_log_to_an_open_log(self):
        # log 2 (Lotoroto), then the only open log (3), then YES
        self.run_title_menu(COPY, [DOWN, ENTER, ENTER, ENTER])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: self.saves[2]}, self.logs())

    def test_copy_lists_the_used_logs_then_only_the_open_logs(self):
        # It used to list all three logs both times, so a used log could be the source of nothing or be overwritten
        self.game.title_menu.save_dir_contents = self.game.title_menu.save_files()
        with patch.object(OptionsScreen, 'choose_log', return_value=1) as choose_log, \
                patch.object(OptionsScreen, 'choose_open_log', return_value=None) as choose_open_log, \
                self.no_screenshot_menu():
            self.assertIs(BACK_TO_TITLE_MENU, self.game.title_menu.copy_quest())
        self.assertEqual([(1, 'Erdrick'), (2, 'Lotoroto')], choose_log.call_args.args[0])
        self.assertEqual([3], choose_open_log.call_args.args[0])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_no_in_the_copy_confirmation_copies_nothing(self):
        self.run_title_menu(COPY, [ENTER, ENTER, DOWN, ENTER])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_b_in_the_open_logs_window_copies_nothing(self):
        self.run_title_menu(COPY, [ENTER, B])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_b_in_the_copy_confirmation_copies_nothing(self):
        self.run_title_menu(COPY, [ENTER, ENTER, B])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_b_in_the_copy_from_window_copies_nothing(self):
        self.run_title_menu(COPY, [B])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_esc_backs_out_of_copy_and_erase(self):
        self.run_title_menu(COPY, [ENTER, ESC])
        self.run_title_menu(ERASE, [ESC])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_copy_is_not_on_the_title_menu_with_every_log_used(self):
        # ContChngErsDat: CONTINUE A QUEST, CHANGE MESSAGE SPEED, ERASE AN ADVENTURE LOG; ERASE is entry 2 there
        with open(self.save_path(3), 'w') as save_file:
            json.dump(self.saves[1], save_file)
        with patch.object(self.game.game_functions, 'main_menu_selection', return_value=2) as title_menu, \
                patch.object(self.game.title_menu, 'erase_quest') as erase_quest, \
                patch.object(self.game.title_menu, 'copy_quest') as copy:
            self.game.title_menu.show_title_menu(self.game.screen)
        self.assertEqual(CONTINUE_CHANGE_ERASE_LAYOUT, title_menu.call_args.args[2])
        erase_quest.assert_called_once()
        copy.assert_not_called()

    # ERASE AN ADVENTURE LOG

    def test_erase_asks_first_and_erases_on_yes(self):
        # log 2, then YES
        self.run_title_menu(ERASE, [DOWN, ENTER, ENTER])
        self.assertEqual({1: self.saves[1], 2: None, 3: None}, self.logs())

    def test_no_in_the_erase_confirmation_erases_nothing(self):
        # It used to erase the log as soon as it was chosen
        self.run_title_menu(ERASE, [DOWN, ENTER, DOWN, ENTER])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_b_in_the_erase_confirmation_erases_nothing(self):
        self.run_title_menu(ERASE, [ENTER, B])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_b_in_the_erase_log_window_erases_nothing(self):
        self.run_title_menu(ERASE, [B])
        self.assertEqual({1: self.saves[1], 2: self.saves[2], 3: None}, self.logs())

    def test_erase_shows_the_logs_hero_and_level(self):
        self.game.title_menu.save_dir_contents = self.game.title_menu.save_files()
        with patch.object(OptionsScreen, 'choose_log', return_value=2), \
                patch.object(OptionsScreen, 'confirm_erase', return_value=False) as confirm_erase, \
                self.no_screenshot_menu():
            self.assertIs(BACK_TO_TITLE_MENU, self.game.title_menu.erase_quest())
        confirm_erase.assert_called_once_with('Lotoroto', 2)


class TestLogWindows(OptionsTestCase):

    def test_erase_log_window(self):
        # EraseLogDat: double spaced, each line after a blank tile; the level in 2 digits after "LEVEL" and 2 blanks
        window = erase_log_window('Lotoroto', 2, gettext.gettext)
        self.assertEqual(ERASE_LOG_WINDOW, window.window)
        self.assertEqual(((2, 2, 'Lotoroto'), (2, 4, 'LEVEL'), (9, 4, ' 2'), (2, 6, 'Do You Want To'),
                          (2, 8, 'Erase This'), (2, 10, 'Character?')), window.prompt)
        self.assertEqual((), window.labels)

    def test_erase_log_window_in_korean(self):
        window = erase_log_window('Lotoroto', 12, set_gettext_language('Korean'))
        self.assertEqual(((2, 2, 'Lotoroto'), (2, 4, '레벨'), (9, 4, '12'), (2, 6, '이 캐릭터를'),
                          (2, 8, '지우시겠습니까?')), window.prompt)

    def test_yes_no_window(self):
        # YesNo2Dat: Y = 3, X = 10, YES then NO, cursor home Y = 2, X = 1
        window = yes_no_options(gettext.gettext)
        self.assertEqual(YES_NO_2_WINDOW, window.window)
        self.assertEqual(('YES', 'NO'), window.labels)
        self.assertEqual([(1, 2), (1, 4)], [(window.entry_cursor_column(i), window.entry_row(i)) for i in (0, 1)])
        self.assertEqual(('예', '아니오'), yes_no_options(set_gettext_language('Korean')).labels)

    def test_open_logs_window(self):
        # LogList13Dat1: one line per open log, no colon and no name; one block high plus one per log
        window = open_log_options([1, 3])
        self.assertEqual(ADVENTURE_LOG_WINDOW_1._replace(height=3), window.window)
        self.assertEqual(('ADVENTURE LOG 1', 'ADVENTURE LOG 3'), window.labels)

    def test_open_logs_window_opens_over_the_used_logs_window(self):
        screen = OptionsScreen(self.game.screen, self.config)
        with patch('src.selection.event.get', side_effect=presses(DOWN, ENTER, DOWN, ENTER)):
            self.assertEqual(2, screen.choose_log([(1, 'Erdrick'), (2, 'Lotoroto')]))
            self.assertEqual(3, screen.choose_open_log([1, 3]))
        self.assertEqual([1, 1], [index for _, index in screen.windows])


class TestContinueWithOneLog(OptionsTestCase):

    def test_b_goes_back_to_the_title_menu(self):
        # B on the one-log CONTINUE A QUEST screen used to do nothing
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.game.directories.save_dir = tmp_dir.name
        with open(os.path.join(tmp_dir.name, 'save_slot_1.json'), 'w') as save_file:
            json.dump({'Name': 'Erdrick', 'Experience': 0}, save_file)
        self.game.title_menu.save_dir_contents = self.game.title_menu.save_files()
        # B, then A (which would continue the quest if B were ignored)
        with patch('src.selection.event.get', side_effect=[[B], [ENTER]]), \
                patch.object(self.game, 'load_game') as load_game:
            self.assertIs(BACK_TO_TITLE_MENU, self.game.title_menu.continue_quest())
        load_game.assert_not_called()

    def test_a_still_continues(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.game.directories.save_dir = tmp_dir.name
        with open(os.path.join(tmp_dir.name, 'save_slot_1.json'), 'w') as save_file:
            json.dump({'Name': 'Erdrick', 'Experience': 0}, save_file)
        self.game.title_menu.save_dir_contents = self.game.title_menu.save_files()
        with patch('src.selection.event.get', side_effect=[[ENTER]]), \
                patch.object(self.game, 'load_game') as load_game:
            self.game.title_menu.continue_quest()
        load_game.assert_called_once()


class TestNewQuestLog(OptionsTestCase):
    """BEGIN A NEW QUEST's log window (DoNewQuest -> ShowOpenLogs): B goes back to the title menu (WndBackToMain)."""

    def setUp(self):
        super().setUp()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.game.directories.save_dir = self.tmp_dir.name

    def new_quest(self, keys):
        """The real title menu with no logs, played key by key (one key per frame), up to the name entry."""
        with patch('src.selection.event.get', side_effect=[[key] for key in keys]), \
                patch('src.title_menu.NameSelection') as name_selection, \
                patch.object(self.game.title_menu, 'choose_new_quest_options'), \
                patch.object(self.game, 'start_at_throne_room'):
            self.game.title_menu.show_main_menu_screen(self.game.screen)
        return name_selection

    def test_b_in_the_log_window_goes_back_to_the_title_menu(self):
        # It used to do nothing, so the next A chose log 1
        # BEGIN A NEW QUEST, B; BEGIN A NEW QUEST again, then log 2
        name_selection = self.new_quest([ENTER, B, ENTER, DOWN, ENTER])
        name_selection.assert_called_once()
        self.assertEqual(2, self.game.player.adventure_log)

    def test_esc_in_the_log_window_goes_back_to_the_title_menu(self):
        name_selection = self.new_quest([ENTER, ESC, ENTER, DOWN, DOWN, ENTER])
        name_selection.assert_called_once()
        self.assertEqual(3, self.game.player.adventure_log)

    def test_b_goes_back_before_the_name_entry(self):
        with patch('src.selection.event.get', side_effect=[[B]]), \
                patch('src.title_menu.NameSelection') as name_selection:
            self.assertIs(BACK_TO_TITLE_MENU, self.game.title_menu.begin_new_quest())
        name_selection.assert_not_called()
        self.assertEqual(0, self.game.player.adventure_log)
