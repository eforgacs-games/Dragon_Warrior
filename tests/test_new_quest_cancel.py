"""Escape in the name entry leaves BEGIN A NEW QUEST: back to the title menu, with no game started and nothing saved."""
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import K_ESCAPE, K_RETURN, K_TAB, KEYDOWN

from src.config.test_config import test_config
from src.game import BACK_TO_TITLE_MENU, Game


def key_event(key: int, unicode: str = '') -> MagicMock:
    current_event = MagicMock()
    current_event.type = KEYDOWN
    current_event.key = key
    current_event.unicode = unicode
    return current_event


ESCAPE = key_event(K_ESCAPE, '\x1b')


class TestNewQuestCancel(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.save_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.save_dir.cleanup)
        with patch('src.game.SCALED'):
            self.game = Game({**test_config, 'SAVE_DIR': self.save_dir.name})
        self.game.cmd_menu = MagicMock()

    def begin_new_quest(self, name_entry_events: list):
        with patch.object(self.game.game_functions, 'main_menu_selection', return_value=0), \
                patch('src.menu_functions.event.get', side_effect=[[e] for e in name_entry_events]), \
                patch('src.menu_functions.display'), patch('src.menu_functions.Sound'), \
                patch('src.menu_functions.toggle_joystick_input', return_value=True), \
                patch.object(self.game, 'choose_new_quest_options') as choose_options, \
                patch.object(self.game, 'start_at_throne_room') as start:
            result = self.game.begin_new_quest()
        return result, choose_options, start

    def assert_cancelled(self, result, choose_options, start):
        self.assertIs(BACK_TO_TITLE_MENU, result)
        choose_options.assert_not_called()
        start.assert_not_called()
        self.assertEqual([], os.listdir(self.save_dir.name))

    def test_escape_while_typing_goes_back_to_the_title_menu(self):
        self.assert_cancelled(*self.begin_new_quest([key_event(pygame.K_e, 'E'), ESCAPE]))

    def test_escape_with_joystick_input_goes_back_to_the_title_menu(self):
        self.assert_cancelled(*self.begin_new_quest([key_event(K_TAB), ESCAPE]))

    def test_a_name_still_starts_the_quest(self):
        result, choose_options, start = self.begin_new_quest([key_event(pygame.K_e, 'E'), key_event(K_RETURN)])
        self.assertIsNone(result)
        self.assertEqual('E', self.game.player.name)
        choose_options.assert_called_once()
        start.assert_called_once()

    def test_the_title_menu_is_shown_again(self):
        # No logs: the title menu is BEGIN A NEW QUEST only. Escape in the name entry, then the title menu again,
        # and this time a name: the quest starts.
        name_entry_events = [ESCAPE, key_event(pygame.K_a, 'A'), key_event(K_RETURN)]
        with patch.object(self.game.game_functions, 'main_menu_selection', return_value=0) as menu, \
                patch('src.menu_functions.event.get', side_effect=[[e] for e in name_entry_events]), \
                patch('src.menu_functions.display'), patch('src.menu_functions.Sound'), \
                patch.object(self.game, 'choose_new_quest_options'), \
                patch.object(self.game, 'start_at_throne_room') as start:
            self.game.show_main_menu_screen(self.game.screen)
        # the title menu, the log, (Escape) the title menu again, the log
        self.assertEqual(4, menu.call_count)
        start.assert_called_once()
        self.assertEqual('A', self.game.player.name)
        self.assertEqual([], os.listdir(self.save_dir.name))
