from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import KEYDOWN, K_DOWN, QUIT

from src.config.test_config import test_config
from tests.helpers import new_game


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
        self.dialog_lookup = new_game().cmd_menu.dialog_lookup

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
                patch.object(menu.game.music_player, 'stop_music', side_effect=lambda: events.append('stop')), \
                patch.object(self.dialog_lookup, 'wait_for_reset', side_effect=lambda: events.append('hang')):
            self.dialog_lookup.rest_then_for_awhile()
        self.assertEqual(events, ["Rest then for awhile.", 'stop',
                                  "Please push RESET, hold it in, then turn off the POWER.",
                                  "If you turn the power off first, the Imperial Scroll of Honor containing your deeds "
                                  "may be lost.", 'hang'])

    def test_reset_message_is_in_its_own_new_dialog_window(self):
        # NES ExitGame: EndGameClearPPU, then Dowindow WND_DIALOG, a new empty window, before the reset message.
        # The King's "Rest then for awhile." must not still be in the window above it.
        menu = self.dialog_lookup.command_menu
        text_before_reset_message = []

        def show(line, **_):
            if line.startswith("Please push RESET"):
                text_before_reset_message.extend(row for row in menu.dialog_buffer.visible_lines if row.strip())
            else:
                list(menu.dialog_buffer.print_message(line, quoted=False))

        with patch.object(menu, 'show_line_in_dialog_box', side_effect=show), \
                patch.object(menu.game.music_player, 'stop_music'), \
                patch.object(self.dialog_lookup, 'wait_for_reset'):
            self.dialog_lookup.rest_then_for_awhile()
        self.assertEqual(text_before_reset_message, [])

    def test_reset_message_waits_only_after_the_first_sentence(self):
        # NES TextBlock19 entry 8: WAIT after "...turn off the POWER.", then the second sentence ends with no wait
        menu = self.dialog_lookup.command_menu
        with patch.object(menu, 'show_line_in_dialog_box') as show_line, \
                patch.object(menu.game.music_player, 'stop_music'), \
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
        with patch('src.selection.event.get', side_effect=[mashed]), \
                patch.object(self.dialog_lookup.command_menu, 'show_line_in_dialog_box'), \
                patch.object(self.dialog_lookup.command_menu, 'show_text_in_dialog_box'), \
                patch.object(self.dialog_lookup.command_menu, 'window_drop_down_effect'), \
                patch('data.text.dialog_lookup_table.screen_fade'):
            self.dialog_lookup.check_stay_at_inn(6)
        self.assertEqual(player.gold, 94)

    def test_closing_the_window_in_a_selection_window_quits_the_game(self):
        # It used to call the builtin quit(), which exits without pygame.quit() (and isn't there in every Python)
        from src.windows import SHOP_INVENTORY_WINDOW
        with patch('data.text.dialog_lookup_table.get', side_effect=[[pygame.event.Event(QUIT)]]), \
                patch('data.text.dialog_lookup_table.display'), \
                patch.object(self.dialog_lookup.command_menu, 'window_drop_down_effect'), \
                patch('src.waiting.pygame_quit') as pygame_quit, self.assertRaises(SystemExit):
            self.dialog_lookup.select_in_window(SHOP_INVENTORY_WINDOW, 2, lambda: None, 2)
        pygame_quit.assert_called_once()

    def test_closing_the_window_after_the_bad_ending_quits_the_game(self):
        with patch('data.text.dialog_lookup_table.get', side_effect=[[pygame.event.Event(QUIT)]]), \
                patch('data.text.dialog_lookup_table.time.wait'), \
                patch('src.waiting.pygame_quit') as pygame_quit, self.assertRaises(SystemExit):
            self.dialog_lookup.bad_ending_spinlock()
        pygame_quit.assert_called_once()
