from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import KEYDOWN, K_DOWN, QUIT

from src.config.test_config import test_config
from src.game import Game


class TestDialogLookup(TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.dialog_lookup = Game(test_config).cmd_menu.dialog_lookup

    def test_inn_costs_match_nes(self):
        # NES InnCostTbl (Bank00): Kol 20, Brecconary 6, Garinham 25, Cantlin 100, Rimuldar 55
        expected = {'Brecconary': 6, 'Garinham': 25, 'Kol': 20, 'Rimuldar': 55, 'Cantlin': 100}
        found = {}
        for town, characters in self.dialog_lookup.lookup_table.items():
            for character in characters.values():
                dialog = character.get('dialog') if isinstance(character, dict) else None
                for entry in dialog if isinstance(dialog, tuple) else ():
                    if getattr(getattr(entry, 'func', None), '__name__', '') == 'check_stay_at_inn':
                        found.setdefault(town, set()).add(entry.args[0])
        self.assertEqual(found, {town: {cost} for town, cost in expected.items()})

    def test_not_continuing_the_quest_silences_the_music(self):
        # NES ContQuestDialog -> ExitGame (Bank01): "Rest then for awhile." is shown with the music still playing,
        # then MSC_NOSOUND silences it before the black screen and the reset message
        events = []
        menu = self.dialog_lookup.command_menu
        with patch.object(menu, 'show_line_in_dialog_box', side_effect=lambda line, **_: events.append(line)), \
                patch('data.text.dialog_lookup_table.mixer.music.stop', side_effect=lambda: events.append('stop')), \
                patch.object(self.dialog_lookup, 'wait_for_reset', side_effect=lambda: events.append('hang')):
            self.dialog_lookup.rest_then_for_awhile()
        self.assertEqual(events, ["Rest then for awhile.", 'stop',
                                  "Please push RESET, hold it in, then turn off the POWER.",
                                  "If you turn the power off first, the Imperial Scroll of Honor containing your deeds "
                                  "may be lost.", 'hang'])

    def test_reset_message_waits_only_after_the_first_sentence(self):
        # NES TextBlock19 entry 8: WAIT after "...turn off the POWER.", then the second sentence ends with no wait
        menu = self.dialog_lookup.command_menu
        with patch.object(menu, 'show_line_in_dialog_box') as show_line, \
                patch('data.text.dialog_lookup_table.mixer.music.stop'), \
                patch.object(self.dialog_lookup, 'wait_for_reset'):
            self.dialog_lookup.rest_then_for_awhile()
        first, second = show_line.call_args_list[1:]
        self.assertFalse(first.kwargs.get('skip_text', False))
        self.assertTrue(second.kwargs['skip_text'])

    def test_after_the_reset_message_only_closing_the_window_does_anything(self):
        # NES Spinlock2: every button is ignored; closing the window stands in for reset
        from pygame import K_j, K_k, K_RETURN
        from pygame.event import Event
        key_presses = [[Event(KEYDOWN, key=key, unicode='', mod=0)] for key in (K_k, K_j, K_RETURN, K_DOWN)]
        with patch('data.text.dialog_lookup_table.get', side_effect=key_presses + [[Event(QUIT)]]) as get_events, \
                patch('data.text.dialog_lookup_table.time.wait'), patch('src.waiting.pygame_quit'):
            with self.assertRaises(SystemExit):
                self.dialog_lookup.wait_for_reset()
        self.assertEqual(get_events.call_count, len(key_presses) + 1)

    def test_mashing_accept_at_the_inn_stays_and_pays_once(self):
        # Issue #97: mashing the accept key restarted the stay and charged for it again
        from pygame import KEYDOWN, K_RETURN
        from pygame.event import Event
        player = self.dialog_lookup.player
        player.gold = 100
        mashed = [Event(KEYDOWN, key=K_RETURN, unicode='\r') for _ in range(3)]
        with patch('data.text.dialog.get', side_effect=[mashed]), \
                patch.object(self.dialog_lookup.command_menu, 'show_line_in_dialog_box'), \
                patch.object(self.dialog_lookup.command_menu, 'show_text_in_dialog_box'), \
                patch.object(self.dialog_lookup.command_menu, 'window_drop_down_effect'), \
                patch('data.text.dialog_lookup_table.fade'):
            self.dialog_lookup.check_stay_at_inn(6)
        self.assertEqual(player.gold, 94)
